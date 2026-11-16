"""A fake Telegram API session and a fake backend, so handlers run through the real dispatcher."""

import itertools
import time
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    GetFile,
    SendDocument,
    SendMessage,
    TelegramMethod,
)
from aiogram.types import File, Message, Update

from universe_bot.app import build_dispatcher
from universe_bot.backend import BackendError, Output, Result
from universe_bot.config import Settings
from universe_bot.storage import MemoryStore

BOT_ID = 42
USER = {"id": 1001, "is_bot": False, "first_name": "Ali", "language_code": "uz"}
_ids = itertools.count(100)


class FakeSession(BaseSession):
    """Records every Bot API call and answers with plausible objects."""

    def __init__(self, files: dict[str, bytes] | None = None):
        super().__init__()
        self.calls: list[TelegramMethod] = []
        self.files = files or {}

    def of(self, kind: type) -> list:
        return [c for c in self.calls if isinstance(c, kind)]

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None) -> Any:
        self.calls.append(method)
        if isinstance(method, GetFile):
            return File(file_id=method.file_id, file_unique_id=method.file_id, file_path=f"files/{method.file_id}")
        if isinstance(method, SendMessage | SendDocument | EditMessageText):
            chat_id = getattr(method, "chat_id", None) or USER["id"]
            text = getattr(method, "text", None)
            return Message.model_validate(
                {
                    "message_id": next(_ids),
                    "date": int(time.time()),
                    "chat": {"id": chat_id, "type": "private"},
                    "text": text,
                }
            )
        if isinstance(method, AnswerCallbackQuery):
            return True
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        yield self.files.get(url.rsplit("/", 1)[-1], b"telegram-file-bytes")

    async def close(self) -> None:
        pass


class FakeBackend:
    """Stands in for BackendClient. Set `result` or `error` before pressing a button."""

    def __init__(self) -> None:
        self.created: list[dict] = []
        self.result = Result([Output("out.pdf", 1000, "/api/v1/files/1/?t=x")], None)
        self.error: BackendError | None = None
        self.downloads: list[str] = []

    async def create_task(self, telegram_id: int, tool: str, options: dict, files: list[tuple[str, bytes]]) -> dict:
        self.created.append({"telegram_id": telegram_id, "tool": tool, "options": options, "files": files})
        if self.error and self.error.code in {"daily_limit_reached", "throttled", "unsupported_format"}:
            raise self.error
        return {"id": "task-1"}

    async def wait(self, telegram_id: int, task_id: str, max_wait: float, interval: float = 1.0) -> Result:
        if self.error:
            raise self.error
        return self.result

    async def download(self, path: str) -> bytes:
        self.downloads.append(path)
        return b"%PDF-result"


class Harness:
    def __init__(self) -> None:
        self.session = FakeSession()
        self.bot = Bot("42:TEST", session=self.session)
        self.store = MemoryStore()
        self.backend = FakeBackend()
        self.settings = Settings(
            bot_token="42:TEST",
            backend_url="http://backend:8000",
            public_origin="https://universe.test",
            bot_api_secret="s",
            redis_url="",
            webhook_url="",
            webhook_secret="",
            webhook_host="",
            webhook_port=0,
        )
        self.dp = build_dispatcher(self.store, self.backend, self.settings)
        self.dp["albums"]._delay = 0.05
        self._update_ids = itertools.count(1)

    async def send(self, user: dict | None = None, chat_type: str = "private", **message: Any) -> None:
        user = user or USER
        payload = {
            "message_id": next(_ids),
            "date": int(time.time()),
            "chat": {"id": user["id"] if chat_type == "private" else -500, "type": chat_type},
            "from": user,
            **message,
        }
        await self.dp.feed_update(
            self.bot, Update.model_validate({"update_id": next(self._update_ids), "message": payload})
        )

    async def press(self, data: str, user: dict | None = None) -> None:
        user = user or USER
        message = {
            "message_id": next(_ids),
            "date": int(time.time()),
            "chat": {"id": user["id"], "type": "private"},
            "text": "x",
        }
        update = {
            "update_id": next(self._update_ids),
            "callback_query": {
                "id": str(next(_ids)),
                "from": user,
                "chat_instance": "c",
                "data": data,
                "message": message,
            },
        }
        await self.dp.feed_update(self.bot, Update.model_validate(update))

    async def albums_done(self) -> None:
        await self.dp["albums"].drain()

    def texts(self) -> list[str]:
        return [c.text for c in self.session.calls if isinstance(c, SendMessage | EditMessageText)]

    def buttons(self) -> list[tuple[str, str]]:
        """(text, callback_data) of the last message that had inline buttons."""
        for call in reversed(self.session.of(SendMessage)):
            if call.reply_markup:
                return [(b.text, b.callback_data) for row in call.reply_markup.inline_keyboard for b in row]
        return []


@pytest.fixture
def h() -> Harness:
    return Harness()


def document(name: str, size: int = 1000, mime: str = "application/octet-stream", file_id: str | None = None) -> dict:
    fid = file_id or f"doc-{name}"
    return {
        "document": {"file_id": fid, "file_unique_id": fid, "file_name": name, "file_size": size, "mime_type": mime}
    }


def photo(file_id: str, size: int = 50_000) -> dict:
    return {"photo": [{"file_id": file_id, "file_unique_id": file_id, "width": 800, "height": 600, "file_size": size}]}
