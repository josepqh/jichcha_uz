"""Client for the Django API. The bot calls it as a trusted internal client (see backend identity.py)."""

import asyncio
import json
from dataclasses import dataclass

import aiohttp

DONE, FAILED = "done", "failed"


class BackendError(Exception):
    """A failure with an error code the user can be told about (translated in texts.py)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Output:
    name: str
    size: int
    url: str  # path with its signed token, e.g. /api/v1/files/<id>/?t=...


@dataclass(frozen=True)
class Result:
    outputs: list[Output]
    bundle: Output | None  # all outputs in one zip, when the tool makes one


def _output(data: dict) -> Output:
    return Output(data["name"], data["size"], data["download_url"])


class BackendClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, secret: str):
        self._session = session
        self._base = base_url.rstrip("/")
        self._secret = secret

    def _headers(self, telegram_id: int) -> dict[str, str]:
        return {"X-Bot-Secret": self._secret, "X-Telegram-User-Id": str(telegram_id)}

    @staticmethod
    async def _error(resp: aiohttp.ClientResponse) -> BackendError:
        try:
            body = await resp.json(content_type=None)
            code = body.get("error", {}).get("code") or "generic"
        except aiohttp.ContentTypeError, json.JSONDecodeError, AttributeError, ValueError:
            code = "generic"
        return BackendError(code)

    async def create_task(self, telegram_id: int, tool: str, options: dict, files: list[tuple[str, bytes]]) -> dict:
        form = aiohttp.FormData()
        form.add_field("tool", tool)
        form.add_field("options", json.dumps(options))
        for name, data in files:
            form.add_field("files", data, filename=name, content_type="application/octet-stream")
        try:
            async with self._session.post(
                f"{self._base}/api/v1/tasks/", data=form, headers=self._headers(telegram_id)
            ) as resp:
                if resp.status != 202:
                    raise await self._error(resp)
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise BackendError("generic") from exc

    async def get_task(self, telegram_id: int, task_id: str) -> dict:
        try:
            async with self._session.get(
                f"{self._base}/api/v1/tasks/{task_id}/", headers=self._headers(telegram_id)
            ) as resp:
                if resp.status != 200:
                    raise await self._error(resp)
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise BackendError("generic") from exc

    async def wait(self, telegram_id: int, task_id: str, max_wait: float, interval: float = 1.0) -> Result:
        """Poll until the task finishes. Raises BackendError with the task's error code on failure."""
        try:
            async with asyncio.timeout(max_wait):
                while True:
                    task = await self.get_task(telegram_id, task_id)
                    if task["status"] == DONE:
                        bundle = task.get("bundle")
                        return Result([_output(o) for o in task["outputs"]], _output(bundle) if bundle else None)
                    if task["status"] == FAILED:
                        raise BackendError(task.get("error_code") or "generic")
                    await asyncio.sleep(interval)
        except TimeoutError as exc:
            raise BackendError("timeout") from exc

    async def download(self, path: str) -> bytes:
        try:
            async with self._session.get(f"{self._base}{path}") as resp:
                if resp.status != 200:
                    raise await self._error(resp)
                return await resp.read()
        except aiohttp.ClientError as exc:
            raise BackendError("generic") from exc
