"""Collect the messages of one Telegram album (they arrive as separate updates with one media_group_id)."""

import asyncio
from collections.abc import Awaitable, Callable

from aiogram.types import Message

Flush = Callable[[list[Message]], Awaitable[None]]


class AlbumCollector:
    """Waits until an album has been quiet for `delay` seconds, then hands over all its messages once.

    Kept in process memory: albums arrive within a second, and the bot runs as a single process
    (one polling loop, or one webhook server).
    """

    def __init__(self, flush: Flush, delay: float = 1.0):
        self._flush = flush
        self._delay = delay
        self._items: dict[str, list[Message]] = {}
        self._timers: dict[str, asyncio.Task[None]] = {}

    def add(self, message: Message) -> None:
        group = str(message.media_group_id)
        self._items.setdefault(group, []).append(message)
        if timer := self._timers.get(group):
            timer.cancel()
        self._timers[group] = asyncio.create_task(self._later(group))

    async def _later(self, group: str) -> None:
        await asyncio.sleep(self._delay)
        self._timers.pop(group, None)
        messages = sorted(self._items.pop(group, []), key=lambda m: m.message_id)
        if messages:
            await self._flush(messages)

    async def drain(self) -> None:
        """Wait for pending albums (tests, shutdown)."""
        while self._timers:
            await asyncio.gather(*list(self._timers.values()), return_exceptions=True)
