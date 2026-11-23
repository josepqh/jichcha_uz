"""Small bot state: chosen language, pending offers (file refs behind inline buttons), per-user lock.

Callback data is limited to 64 bytes, so a button carries only a short random token; the files it
refers to wait here for an hour. Redis in production, a dict in tests.
"""

import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Protocol

from redis.asyncio import Redis

JOB_TTL = 3600
LOCK_TTL = 400  # longer than the slowest task; a crashed handler cannot block a user forever
LANG_TTL = 60 * 60 * 24 * 365


@dataclass(frozen=True)
class FileRef:
    file_id: str
    name: str
    size: int


@dataclass(frozen=True)
class Job:
    user_id: int
    family: str
    album: bool
    files: list[FileRef] = field(default_factory=list)

    def dumps(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def loads(cls, raw: str) -> Job:
        data = json.loads(raw)
        return cls(
            user_id=data["user_id"],
            family=data["family"],
            album=data["album"],
            files=[FileRef(**f) for f in data["files"]],
        )


class Store(Protocol):
    async def get_lang(self, user_id: int) -> str | None: ...
    async def set_lang(self, user_id: int, lang: str) -> None: ...
    async def save_job(self, job: Job) -> str: ...
    async def get_job(self, token: str) -> Job | None: ...
    async def acquire(self, user_id: int) -> bool: ...
    async def release(self, user_id: int) -> None: ...


def new_token() -> str:
    return secrets.token_urlsafe(8)


class RedisStore:
    def __init__(self, redis: Redis, prefix: str = "jichchabot"):
        self._r = redis
        self._p = prefix

    async def get_lang(self, user_id: int) -> str | None:
        value = await self._r.get(f"{self._p}:lang:{user_id}")
        return value.decode() if isinstance(value, bytes) else value

    async def set_lang(self, user_id: int, lang: str) -> None:
        await self._r.set(f"{self._p}:lang:{user_id}", lang, ex=LANG_TTL)

    async def save_job(self, job: Job) -> str:
        token = new_token()
        await self._r.set(f"{self._p}:job:{token}", job.dumps(), ex=JOB_TTL)
        return token

    async def get_job(self, token: str) -> Job | None:
        raw = await self._r.get(f"{self._p}:job:{token}")
        return Job.loads(raw.decode() if isinstance(raw, bytes) else raw) if raw else None

    async def acquire(self, user_id: int) -> bool:
        return bool(await self._r.set(f"{self._p}:busy:{user_id}", "1", nx=True, ex=LOCK_TTL))

    async def release(self, user_id: int) -> None:
        await self._r.delete(f"{self._p}:busy:{user_id}")


class MemoryStore:
    """Same behaviour as RedisStore, in process memory (tests, quick local runs)."""

    def __init__(self) -> None:
        self.langs: dict[int, str] = {}
        self.jobs: dict[str, tuple[float, Job]] = {}
        self.busy: dict[int, float] = {}

    async def get_lang(self, user_id: int) -> str | None:
        return self.langs.get(user_id)

    async def set_lang(self, user_id: int, lang: str) -> None:
        self.langs[user_id] = lang

    async def save_job(self, job: Job) -> str:
        token = new_token()
        self.jobs[token] = (time.monotonic() + JOB_TTL, job)
        return token

    async def get_job(self, token: str) -> Job | None:
        entry = self.jobs.get(token)
        return entry[1] if entry and entry[0] > time.monotonic() else None

    async def acquire(self, user_id: int) -> bool:
        if self.busy.get(user_id, 0) > time.monotonic():
            return False
        self.busy[user_id] = time.monotonic() + LOCK_TTL
        return True

    async def release(self, user_id: int) -> None:
        self.busy.pop(user_id, None)
