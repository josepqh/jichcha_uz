"""BackendClient against a small aiohttp server that mimics the Django API."""

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from jichcha_bot.backend import BackendClient, BackendError

SECRET = "bot-secret"


class FakeApi:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.polls = 0
        self.statuses = ["queued", "processing", "done"]
        self.error_code = ""

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_post("/api/v1/tasks/", self.create)
        app.router.add_get("/api/v1/tasks/{id}/", self.detail)
        app.router.add_get("/api/v1/files/{id}/", self.file)
        return app

    async def create(self, request: web.Request) -> web.Response:
        if request.headers.get("X-Bot-Secret") != SECRET:
            return web.json_response({"error": {"code": "forbidden"}}, status=403)
        form = await request.post()
        if self.error_code:
            return web.json_response({"error": {"code": self.error_code, "message": "x", "details": {}}}, status=429)
        upload = form["files"]
        self.created.append(
            {
                "user": request.headers["X-Telegram-User-Id"],
                "tool": form["tool"],
                "options": form["options"],
                "file": (upload.filename, upload.file.read()),
            }
        )
        return web.json_response({"id": "t1", "status": "queued"}, status=202)

    async def detail(self, request: web.Request) -> web.Response:
        status = self.statuses[min(self.polls, len(self.statuses) - 1)]
        self.polls += 1
        body = {
            "id": "t1",
            "status": status,
            "error_code": "corrupt_file" if status == "failed" else "",
            "bundle": None,
        }
        body["outputs"] = (
            [{"name": "a.pdf", "size": 5, "download_url": "/api/v1/files/f1/?t=sig"}] if status == "done" else []
        )
        return web.json_response(body)

    async def file(self, request: web.Request) -> web.Response:
        if request.query.get("t") != "sig":
            return web.json_response({"error": {"code": "file_expired"}}, status=404)
        return web.Response(body=b"%PDF-")


@pytest.fixture
async def api():
    fake = FakeApi()
    server = TestServer(fake.app())
    await server.start_server()
    async with aiohttp.ClientSession() as session:
        yield fake, BackendClient(session, str(server.make_url("")), SECRET)
    await server.close()


async def test_create_sends_identity_options_and_file(api):
    fake, client = api
    task = await client.create_task(777, "office-to-pdf", {"x": 1}, [("referat.docx", b"DOCX")])
    assert task["id"] == "t1"
    assert fake.created == [
        {"user": "777", "tool": "office-to-pdf", "options": '{"x": 1}', "file": ("referat.docx", b"DOCX")}
    ]


async def test_api_errors_keep_their_code(api):
    fake, client = api
    fake.error_code = "daily_limit_reached"
    with pytest.raises(BackendError) as exc:
        await client.create_task(1, "image-convert", {}, [("a.png", b"x")])
    assert exc.value.code == "daily_limit_reached"


async def test_wait_polls_until_done_and_downloads(api):
    fake, client = api
    result = await client.wait(1, "t1", max_wait=5, interval=0.01)
    assert fake.polls == 3
    assert [o.name for o in result.outputs] == ["a.pdf"] and result.bundle is None
    assert await client.download(result.outputs[0].url) == b"%PDF-"


async def test_failed_task_raises_its_error_code(api):
    fake, client = api
    fake.statuses = ["processing", "failed"]
    with pytest.raises(BackendError) as exc:
        await client.wait(1, "t1", max_wait=5, interval=0.01)
    assert exc.value.code == "corrupt_file"


async def test_wait_gives_up(api):
    fake, client = api
    fake.statuses = ["processing"]
    with pytest.raises(BackendError) as exc:
        await client.wait(1, "t1", max_wait=0.1, interval=0.02)
    assert exc.value.code == "timeout"


async def test_backend_down_is_a_generic_error():
    async with aiohttp.ClientSession() as session:
        client = BackendClient(session, "http://127.0.0.1:1", SECRET)
        with pytest.raises(BackendError) as exc:
            await client.get_task(1, "t1")
    assert exc.value.code == "generic"
