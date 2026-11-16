from aiogram.methods import AnswerCallbackQuery, SendDocument, SendMessage

from universe_bot.backend import BackendError, Output, Result
from universe_bot.storage import FileRef, Job

from .conftest import USER, document, photo

OTHER = {"id": 2002, "is_bot": False, "first_name": "Vali", "language_code": "en"}
MB = 1024 * 1024


async def test_start_speaks_the_users_language(h):
    await h.send(user={**USER, "language_code": "ru"}, text="/start")
    assert h.texts()[-1].startswith("Здравствуйте! Я бот <b>Universe</b>.")
    await h.send(user={**USER, "language_code": "de"}, text="/start")
    assert h.texts()[-1].startswith("Salom!")  # unknown language falls back to Uzbek


async def test_lang_command_remembers_the_choice(h):
    await h.send(text="/lang")
    assert [text for text, _ in h.buttons()] == ["🇺🇿 Oʻzbekcha", "🇷🇺 Русский", "🇬🇧 English"]
    await h.press("l:en")
    assert await h.store.get_lang(USER["id"]) == "en"
    await h.send(text="/start")
    assert h.texts()[-1].startswith("Hi!")


async def test_word_file_gets_word_actions(h):
    await h.send(**document("referat.docx"))
    assert h.texts()[-1] == "<b>referat.docx</b>\nNima qilamiz?"
    assert [text for text, _ in h.buttons()] == ["📄 PDF qilish", "📚 EPUB"]


async def test_epub_is_not_offered_epub_again(h):
    await h.send(**document("kitob.epub"))
    assert [text for text, _ in h.buttons()] == ["📄 PDF qilish", "📚 MOBI", "📚 AZW3 (Kindle)"]


async def test_pressing_a_button_converts_and_sends_the_result(h):
    await h.send(**document("referat.docx"))
    pdf_button = h.buttons()[0][1]
    await h.press(pdf_button)

    [created] = h.backend.created
    assert created["telegram_id"] == USER["id"]
    assert created["tool"] == "office-to-pdf"
    assert created["files"] == [("referat.docx", b"telegram-file-bytes")]
    [sent] = h.session.of(SendDocument)
    assert sent.document.filename == "out.pdf"
    assert h.texts()[-2:] == ["⏳ Ishlanmoqda…", "✅ Tayyor. Fayllar serverdan avtomatik oʻchiriladi."]
    assert await h.store.acquire(USER["id"])  # the lock was released


async def test_someone_elses_button_does_nothing(h):
    await h.send(**document("referat.docx"))
    button = h.buttons()[0][1]
    await h.press(button, user=OTHER)
    assert not h.backend.created
    [answer] = h.session.of(AnswerCallbackQuery)
    assert answer.show_alert and answer.text == "This button has expired. Send the file again."


async def test_unknown_or_tampered_button(h):
    await h.press("a:nosuchtoken:pdf")
    await h.send(**document("referat.docx"))
    token = h.buttons()[0][1].split(":")[1]
    await h.press(f"a:{token}:extract")  # not an action for Word files
    assert not h.backend.created
    assert all(a.show_alert for a in h.session.of(AnswerCallbackQuery))


async def test_one_job_at_a_time(h):
    await h.send(**document("referat.docx"))
    await h.store.acquire(USER["id"])  # something is already running
    await h.press(h.buttons()[0][1])
    assert not h.backend.created
    assert h.session.of(AnswerCallbackQuery)[-1].text == "Oldingi fayl hali ishlanmoqda. Tugashini kuting."


async def test_backend_errors_are_explained(h):
    h.backend.error = BackendError("daily_limit_reached")
    await h.send(**document("referat.docx"))
    await h.press(h.buttons()[0][1])
    assert h.texts()[-1] == "Bugungi limit tugadi. Ertaga yana urinib koʻring."
    assert await h.store.acquire(USER["id"])


async def test_unknown_error_codes_get_a_generic_message(h):
    h.backend.error = BackendError("something_new")
    await h.send(**document("a.pdf"))
    await h.press(h.buttons()[0][1])
    assert h.texts()[-1] == "Xatolik yuz berdi. Birozdan keyin qayta urinib koʻring."


async def test_files_over_20_mb_get_a_website_link(h):
    await h.send(**document("katta.pdf", size=25 * MB))
    text = h.texts()[-1]
    assert "25.0 MB" in text and "https://universe.test/uz/tools/pdf-compress" in text
    assert not h.buttons()


async def test_unsupported_file(h):
    await h.send(**document("dastur.exe"))
    assert h.texts()[-1].startswith("Bu turdagi faylni hozircha")


async def test_album_of_photos_becomes_one_pdf(h):
    for i in range(3):
        await h.send(media_group_id="album-1", **photo(f"p{i}"))
    await h.albums_done()
    assert h.texts()[-1] == "3 ta fayl. Nima qilamiz?"
    assert [text for text, _ in h.buttons()] == ["📄 PDF qilish", "🗜 Hajmini kichraytirish"]
    await h.press(h.buttons()[0][1])
    [created] = h.backend.created
    assert created["tool"] == "images-to-pdf"
    assert len(created["files"]) == 3


async def test_album_of_pdfs_can_be_merged(h):
    for name in ("a.pdf", "b.pdf"):
        await h.send(media_group_id="album-2", **document(name, mime="application/pdf"))
    await h.albums_done()
    assert [text for text, _ in h.buttons()][0] == "🔗 Birlashtirish"


async def test_mixed_album_is_refused(h):
    await h.send(media_group_id="album-3", **photo("p1"))
    await h.send(media_group_id="album-3", **document("a.pdf"))
    await h.albums_done()
    assert h.texts()[-1].startswith("Albomda turli xil fayllar bor.")


async def test_many_outputs_arrive_as_one_zip(h):
    pages = [Output(f"page-{i}.jpg", 1000, f"/api/v1/files/{i}/?t=x") for i in range(25)]
    h.backend.result = Result(pages, Output("universe-pdf-to-images.zip", 9000, "/api/v1/files/zip/?t=x"))
    await h.send(**document("a.pdf"))
    await h.press(h.buttons()[1][1])  # JPG
    [sent] = h.session.of(SendDocument)
    assert sent.document.filename == "universe-pdf-to-images.zip"


async def test_too_big_result_is_sent_as_a_link(h):
    h.backend.result = Result([Output("big.pdf", 60 * MB, "/api/v1/files/9/?t=sig")], None)
    await h.send(**document("a.pdf"))
    await h.press(h.buttons()[0][1])
    assert not h.session.of(SendDocument)
    assert any("https://universe.test/api/v1/files/9/?t=sig" in t for t in h.texts())


async def test_group_chats_are_ignored(h):
    await h.send(chat_type="group", **document("referat.docx"))
    await h.send(chat_type="supergroup", text="/start")
    assert not h.session.of(SendMessage)


async def test_file_names_are_escaped_in_html(h):
    await h.send(**document("<b>x</b>.docx"))
    assert h.texts()[-1].startswith("<b>&lt;b&gt;x&lt;/b&gt;.docx</b>")


async def test_job_roundtrip():
    job = Job(user_id=1, family="pdf", album=True, files=[FileRef("f", "a.pdf", 3)])
    assert Job.loads(job.dumps()) == job
