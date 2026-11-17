"""Small load test for the API (no extra tools: aiohttp only). Not a benchmark: run it against a
production-like stack (gunicorn + workers) and compare runs on the same machine.

    python deploy/loadtest/run.py http://127.0.0.1:8001 --seconds 20 --concurrency 50

Over plain HTTP run the server with GUEST_COOKIE_SECURE=false, or the client drops the guest cookie.
"""

import argparse
import asyncio
import io
import json
import statistics
import time

import aiohttp


def png_bytes() -> bytes:
    # A tiny valid PNG (1x1), so the test measures the platform, not image size.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360f8cfc0f01f0005fe02fea7d6a6"
        "bf0000000049454e44ae426082"
    )


def summary(name: str, latencies: list[float], errors: dict[str, int], seconds: float) -> str:
    if not latencies:
        return f"{name}: no successful requests, errors={errors}"
    q = statistics.quantiles(latencies, n=100)
    return (
        f"{name}: {len(latencies)} ok in {seconds:.0f}s = {len(latencies) / seconds:.0f} req/s | "
        f"p50 {q[49] * 1000:.0f} ms, p95 {q[94] * 1000:.0f} ms, p99 {q[98] * 1000:.0f} ms | errors {errors or 0}"
    )


async def hammer(base: str, path: str, seconds: float, concurrency: int) -> str:
    latencies: list[float] = []
    errors: dict[str, int] = {}
    deadline = time.monotonic() + seconds

    async def user(session: aiohttp.ClientSession) -> None:
        while time.monotonic() < deadline:
            start = time.monotonic()
            try:
                async with session.get(base + path) as resp:
                    await resp.read()
                    if resp.status == 200:
                        latencies.append(time.monotonic() - start)
                    else:
                        errors[str(resp.status)] = errors.get(str(resp.status), 0) + 1
            except aiohttp.ClientError as exc:
                errors[type(exc).__name__] = errors.get(type(exc).__name__, 0) + 1

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(user(session) for _ in range(concurrency)))
    return summary(f"GET {path}", latencies, errors, seconds)


async def conversions(base: str, users: int) -> str:
    """Each user (own cookie jar = own guest) uploads one PNG -> JPG and waits for the result."""
    accepted: list[float] = []
    finished: list[float] = []
    errors: dict[str, int] = {}

    async def one() -> None:
        # unsafe=True: aiohttp otherwise ignores cookies set by an IP-address host such as 127.0.0.1.
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as session:
            form = aiohttp.FormData()
            form.add_field("tool", "image-convert")
            form.add_field("options", json.dumps({"target": "jpg"}))
            form.add_field("files", io.BytesIO(png_bytes()), filename="a.png", content_type="image/png")
            start = time.monotonic()
            async with session.post(base + "/api/v1/tasks/", data=form) as resp:
                if resp.status != 202:
                    errors[str(resp.status)] = errors.get(str(resp.status), 0) + 1
                    return
                task = await resp.json()
            accepted.append(time.monotonic() - start)
            while True:
                async with session.get(f"{base}/api/v1/tasks/{task['id']}/") as resp:
                    if resp.status == 429:  # polling throttled: back off like the app would
                        errors["poll 429"] = errors.get("poll 429", 0) + 1
                        await asyncio.sleep(2)
                        continue
                    if resp.status != 200:
                        errors[f"poll {resp.status}"] = errors.get(f"poll {resp.status}", 0) + 1
                        return
                    data = await resp.json()
                if data["status"] in ("done", "failed"):
                    if data["status"] == "failed":
                        errors[data["error_code"]] = errors.get(data["error_code"], 0) + 1
                    else:
                        finished.append(time.monotonic() - start)
                    return
                await asyncio.sleep(0.5)

    start = time.monotonic()
    await asyncio.gather(*(one() for _ in range(users)))
    took = time.monotonic() - start
    lines = [
        summary("POST /tasks/ (upload accepted)", accepted, {}, took),
        summary("upload -> result ready", finished, errors, took),
    ]
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--conversions", type=int, default=20)
    parser.add_argument("--only", choices=["read", "convert"], help="Run one scenario.")
    args = parser.parse_args()
    if args.only != "convert":
        print(await hammer(args.base, "/api/v1/tools/", args.seconds, args.concurrency))
        print(await hammer(args.base, "/api/v1/health/", args.seconds / 2, args.concurrency))
    if args.only != "read":
        print(await conversions(args.base, args.conversions))


if __name__ == "__main__":
    asyncio.run(main())
