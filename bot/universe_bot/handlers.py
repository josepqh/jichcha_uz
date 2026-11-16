"""Telegram handlers: file in -> action buttons -> backend task -> files back.

Private chats only: in groups the bot stays silent, so nobody can make it process other
people's files or flood a group with results.
"""

import asyncio
import logging
from pathlib import PurePath

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .actions import WEB_TOOL, Action, actions_for, album_actions_for, family_of, find_action, find_album_action
from .albums import AlbumCollector
from .backend import BackendClient, BackendError, Output, Result
from .config import Settings
from .storage import FileRef, Job, Store
from .texts import LANGUAGE_NAMES, LANGUAGES, error_text, pick_language, t

logger = logging.getLogger(__name__)
MB = 1024 * 1024
MAX_DOCUMENTS = 10  # more outputs than this go out as one zip (or a web link)


class ActionCB(CallbackData, prefix="a"):
    job: str
    act: str


class LangCB(CallbackData, prefix="l"):
    lang: str


async def user_lang(store: Store, user) -> str:
    return await store.get_lang(user.id) or pick_language(user.language_code)


# --- Commands -------------------------------------------------------------------------------------


async def start(message: Message, store: Store) -> None:
    await message.answer(t(await user_lang(store, message.from_user), "start"))


async def help_(message: Message, store: Store, settings: Settings) -> None:
    lang = await user_lang(store, message.from_user)
    await message.answer(t(lang, "help", max_mb=settings.max_download_mb, site=f"{settings.public_origin}/{lang}"))


async def choose_language(message: Message, store: Store) -> None:
    builder = InlineKeyboardBuilder()
    for code in LANGUAGES:
        builder.button(text=LANGUAGE_NAMES[code], callback_data=LangCB(lang=code))
    builder.adjust(3)
    await message.answer(t(await user_lang(store, message.from_user), "lang_prompt"), reply_markup=builder.as_markup())


async def set_language(callback: CallbackQuery, callback_data: LangCB, store: Store) -> None:
    if callback_data.lang not in LANGUAGES:
        await callback.answer()
        return
    await store.set_lang(callback.from_user.id, callback_data.lang)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(t(callback_data.lang, "lang_set"))


# --- Files in -------------------------------------------------------------------------------------


def file_ref(message: Message) -> tuple[FileRef, str] | None:
    """The file in a message and its MIME type. Photos are re-encoded JPEGs by Telegram."""
    if message.document:
        doc = message.document
        return FileRef(doc.file_id, doc.file_name or "file", doc.file_size or 0), doc.mime_type or ""
    if message.photo:
        photo = message.photo[-1]  # largest size
        return FileRef(photo.file_id, f"photo-{message.message_id}.jpg", photo.file_size or 0), "image/jpeg"
    return None


def actions_keyboard(lang: str, token: str, actions: tuple[Action, ...]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action in actions:
        builder.button(text=t(lang, f"act.{action.key}"), callback_data=ActionCB(job=token, act=action.key))
    builder.adjust(2)
    return builder.as_markup()


async def reject_if_too_big(message: Message, lang: str, ref: FileRef, family: str | None, settings: Settings) -> bool:
    if ref.size <= settings.max_download_mb * MB:
        return False
    path = WEB_TOOL.get(family or "", "")
    url = f"{settings.public_origin}/{lang}/{path}".rstrip("/")
    await message.answer(
        t(lang, "too_big", size=round(ref.size / MB, 1), max_mb=settings.max_download_mb, url=url),
        disable_web_page_preview=True,
    )
    return True


async def album_part(message: Message, albums: AlbumCollector) -> None:
    albums.add(message)


async def single_file(message: Message, store: Store, settings: Settings) -> None:
    lang = await user_lang(store, message.from_user)
    found = file_ref(message)
    if not found:
        return
    ref, mime = found
    family = family_of(ref.name, mime)
    if await reject_if_too_big(message, lang, ref, family, settings):
        return
    if family is None or not actions_for(family, ref.name):
        await message.answer(t(lang, "unsupported"))
        return
    token = await store.save_job(Job(user_id=message.from_user.id, family=family, album=False, files=[ref]))
    await message.reply(
        t(lang, "choose", name=_escape(ref.name)),
        reply_markup=actions_keyboard(lang, token, actions_for(family, ref.name)),
    )


async def album_ready(messages: list[Message], store: Store, settings: Settings) -> None:
    first = messages[0]
    lang = await user_lang(store, first.from_user)
    refs: list[FileRef] = []
    families: set[str | None] = set()
    for message in messages:
        found = file_ref(message)
        if not found:
            continue
        ref, mime = found
        family = family_of(ref.name, mime)
        if await reject_if_too_big(message, lang, ref, family, settings):
            return
        refs.append(ref)
        families.add(family)
    if len(families) != 1 or None in families:
        await first.answer(t(lang, "mixed_album" if len(families) > 1 else "unsupported"))
        return
    family = families.pop()
    actions = album_actions_for(family)
    if not actions:
        await first.answer(t(lang, "unsupported"))
        return
    token = await store.save_job(Job(user_id=first.from_user.id, family=family, album=True, files=refs))
    await first.reply(t(lang, "choose_album", count=len(refs)), reply_markup=actions_keyboard(lang, token, actions))


async def anything_else(message: Message, store: Store) -> None:
    await message.answer(t(await user_lang(store, message.from_user), "start"))


# --- Action ---------------------------------------------------------------------------------------


async def run_action(
    callback: CallbackQuery,
    callback_data: ActionCB,
    bot: Bot,
    store: Store,
    backend: BackendClient,
    settings: Settings,
) -> None:
    user = callback.from_user
    lang = await user_lang(store, user)
    job = await store.get_job(callback_data.job)
    # A button only works for the person it was shown to.
    if job is None or job.user_id != user.id or callback.message is None:
        await callback.answer(t(lang, "expired"), show_alert=True)
        return
    find = find_album_action if job.album else find_action
    action = find(job.family, callback_data.act)
    if action is None:
        await callback.answer(t(lang, "expired"), show_alert=True)
        return
    if not await store.acquire(user.id):
        await callback.answer(t(lang, "busy"), show_alert=True)
        return

    await callback.answer()
    status = callback.message
    chat_id = status.chat.id
    try:
        await status.edit_text(t(lang, "working"))
        files = [(ref.name, (await bot.download(ref.file_id)).read()) for ref in job.files]
        task = await backend.create_task(user.id, action.tool, action.options, files)
        result = await backend.wait(user.id, task["id"], max_wait=settings.task_timeout_s)
        await deliver(bot, chat_id, lang, result, backend, settings)
        await status.edit_text(t(lang, "done"))
    except BackendError as exc:
        await _safe_edit(status, error_text(lang, exc.code))
    except TelegramAPIError:
        logger.exception("Telegram API error while processing a file")
        await _safe_edit(status, error_text(lang, "generic"))
    finally:
        await store.release(user.id)


async def deliver(
    bot: Bot, chat_id: int, lang: str, result: Result, backend: BackendClient, settings: Settings
) -> None:
    """Send results as documents; one zip when there are many; a web link when too big for Telegram."""
    outputs = result.outputs
    if len(outputs) > MAX_DOCUMENTS and result.bundle:
        outputs = [result.bundle]
    for output in outputs[:MAX_DOCUMENTS]:
        await send_output(bot, chat_id, lang, output, backend, settings)
        await asyncio.sleep(0.3)  # stay under Telegram's per-chat flood limit
    if len(outputs) > MAX_DOCUMENTS:
        rest = len(outputs) - MAX_DOCUMENTS
        await bot.send_message(chat_id, t(lang, "more_files", count=rest, site=f"{settings.public_origin}/{lang}"))


async def send_output(
    bot: Bot, chat_id: int, lang: str, output: Output, backend: BackendClient, settings: Settings
) -> None:
    if output.size > settings.max_upload_mb * MB:
        await bot.send_message(
            chat_id, t(lang, "result_link", url=f"{settings.public_origin}{output.url}"), disable_web_page_preview=True
        )
        return
    data = await backend.download(output.url)
    name = PurePath(output.name).name or "file"
    await bot.send_document(chat_id, BufferedInputFile(data, filename=name))


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except TelegramAPIError:
        await message.answer(text)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_router() -> Router:
    """A fresh router with every handler. Private chats only: in groups the bot stays silent."""
    router = Router(name="universe")
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

    router.message.register(start, CommandStart())
    router.message.register(help_, Command("help"))
    router.message.register(choose_language, Command("lang"))
    router.callback_query.register(set_language, LangCB.filter())
    router.message.register(album_part, F.media_group_id, F.document | F.photo)
    router.message.register(single_file, F.document | F.photo)
    router.message.register(anything_else)
    router.callback_query.register(run_action, ActionCB.filter())
    return router
