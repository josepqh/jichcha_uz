"""Wiring: bot, dispatcher, storage, backend client; long polling or webhook."""

import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from redis.asyncio import Redis

from .albums import AlbumCollector
from .backend import BackendClient
from .config import Settings
from .handlers import album_ready, make_router
from .storage import RedisStore, Store

logger = logging.getLogger(__name__)
WEBHOOK_PATH = "/telegram/webhook"

COMMANDS = {
    "uz": [("start", "Boshlash"), ("help", "Nima qila olaman"), ("lang", "Tilni oʻzgartirish")],
    "ru": [("start", "Начать"), ("help", "Что я умею"), ("lang", "Сменить язык")],
    "en": [("start", "Start"), ("help", "What I can do"), ("lang", "Change language")],
}


def build_dispatcher(store: Store, backend: BackendClient, settings: Settings) -> Dispatcher:
    dp = Dispatcher()

    async def flush(messages: list[Message]) -> None:
        await album_ready(messages, store, settings)

    dp["store"] = store
    dp["backend"] = backend
    dp["settings"] = settings
    dp["albums"] = AlbumCollector(flush)
    dp.include_router(make_router())
    return dp


async def set_commands(bot: Bot) -> None:
    for lang, commands in COMMANDS.items():
        await bot.set_my_commands(
            [BotCommand(command=c, description=d) for c, d in commands],
            language_code=None if lang == "uz" else lang,
        )


def make_bot(settings: Settings) -> Bot:
    return Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def run_polling(settings: Settings) -> None:
    bot = make_bot(settings)
    redis = Redis.from_url(settings.redis_url)
    timeout = aiohttp.ClientTimeout(total=600, connect=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        dp = build_dispatcher(
            RedisStore(redis), BackendClient(session, settings.backend_url, settings.bot_api_secret), settings
        )
        await set_commands(bot)
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Long polling started")
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            await redis.aclose()
            await bot.session.close()


def run_webhook(settings: Settings) -> None:
    if not settings.webhook_secret:
        raise SystemExit("TELEGRAM_WEBHOOK_SECRET is required in webhook mode.")
    bot = make_bot(settings)
    redis = Redis.from_url(settings.redis_url)
    state: dict[str, aiohttp.ClientSession] = {}

    async def on_startup(app: web.Application) -> None:
        state["session"] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600, connect=10))
        backend = BackendClient(state["session"], settings.backend_url, settings.bot_api_secret)
        dp = build_dispatcher(RedisStore(redis), backend, settings)
        # Telegram echoes secret_token in a header; updates without it are rejected.
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.webhook_secret).register(app, WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        await set_commands(bot)
        await bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.webhook_secret,
            allowed_updates=dp.resolve_used_update_types(),
        )

    async def on_cleanup(app: web.Application) -> None:
        if session := state.get("session"):
            await session.close()
        await redis.aclose()

    app = web.Application()
    app.on_startup.insert(0, on_startup)
    app.on_cleanup.append(on_cleanup)

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/healthz", health)
    web.run_app(app, host=settings.webhook_host, port=settings.webhook_port)
