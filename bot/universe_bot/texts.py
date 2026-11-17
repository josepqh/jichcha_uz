"""Bot messages in Uzbek (Latin), Russian and English. HTML parse mode: keep <b> and <a> balanced."""

LANGUAGES = ("uz", "ru", "en")
DEFAULT = "uz"

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "start": (
            "Salom! Men <b>Universe</b> botiman.\n\n"
            "Menga fayl yuboring: Word, Excel, PowerPoint, PDF, surat yoki arxiv. "
            "Nima qilish mumkinligini tugmalar bilan taklif qilaman.\n\n"
            "Bir nechta suratni bitta albom qilib yuborsangiz, ulardan PDF yasayman."
        ),
        "help": (
            "<b>Nima qila olaman</b>\n"
            "• Word, Excel, PowerPoint → PDF\n"
            "• PDF: siqish, rasmlarga yoki sahifalarga ajratish, birlashtirish\n"
            "• Suratlar: JPG/PNG/WEBP, siqish, PDF qilish\n"
            "• Arxivlar: ochish, ZIP qilish\n\n"
            "Fayl {max_mb} MB gacha. Kattaroq fayllar uchun saytdan foydalaning: {site}\n"
            "Fayllar ishlovdan keyin serverdan oʻchiriladi.\n\n"
            "/lang — tilni oʻzgartirish"
        ),
        "lang_prompt": "Tilni tanlang:",
        "lang_set": "Til oʻzgartirildi: Oʻzbekcha.",
        "choose": "<b>{name}</b>\nNima qilamiz?",
        "choose_album": "{count} ta fayl. Nima qilamiz?",
        "unsupported": "Bu turdagi faylni hozircha qayta ishlay olmayman. Word, Excel, PowerPoint, PDF, surat yoki arxiv yuboring.",
        "mixed_album": "Albomda turli xil fayllar bor. Bir xil turdagi fayllarni yuboring, masalan, faqat suratlar.",
        "too_big": (
            "Fayl {size} MB, Telegram esa botlarga {max_mb} MB gacha faylni ochishga ruxsat beradi.\n"
            'Uni saytda qayta ishlang: <a href="{url}">{url}</a>'
        ),
        "working": "⏳ Ishlanmoqda…",
        "done": "✅ Tayyor. Fayllar serverdan avtomatik oʻchiriladi.",
        "result_link": '📎 Natija Telegram uchun juda katta. Uni shu yerdan yuklab oling (1 soat ichida): <a href="{url}">yuklab olish</a>',
        "busy": "Oldingi fayl hali ishlanmoqda. Tugashini kuting.",
        "more_files": "Yana {count} ta fayl Telegram'ga sigʻmadi. Arxivni saytda oching: {site}",
        "expired": "Bu tugma eskirgan. Faylni qaytadan yuboring.",
        "act.pdf": "📄 PDF qilish",
        "act.jpg": "🖼 JPG",
        "act.png": "🖼 PNG",
        "act.webp": "🖼 WEBP",
        "act.shrink": "🗜 Hajmini kichraytirish",
        "act.split": "✂️ Sahifalarga boʻlish",
        "act.merge": "🔗 Birlashtirish",
        "act.extract": "📂 Arxivni ochish",
        "act.zip": "🗂 ZIP qilish",
        "err.unsupported_format": "Fayl turi bu amalga mos kelmadi. Fayl kengaytmasi uning ichidagiga toʻgʻri kelmasligi mumkin.",
        "err.file_too_large": "Fayl juda katta.",
        "err.daily_limit_reached": "Bugungi limit tugadi. Ertaga yana urinib koʻring.",
        "err.throttled": "Juda koʻp soʻrov. Bir daqiqadan keyin urinib koʻring.",
        "err.corrupt_file": "Faylni ochib boʻlmadi: u buzilgan yoki boshqa formatda.",
        "err.timeout": "Ishlov juda uzoq davom etdi. Kichikroq fayl bilan urinib koʻring.",
        "err.malware_detected": "Faylda zararli dastur topildi. U qayta ishlanmadi va oʻchirildi.",
        "err.scan_unavailable": "Faylni viruslarga tekshirib boʻlmadi. Birozdan keyin qayta urinib koʻring.",
        "err.pdf_encrypted": "PDF parol bilan himoyalangan.",
        "err.archive_encrypted": "Arxiv parol bilan himoyalangan.",
        "err.wrong_password": "Parol notoʻgʻri.",
        "err.archive_too_large": "Arxiv ochilganda juda katta hajm chiqadi.",
        "err.archive_too_many_files": "Arxivda fayllar juda koʻp.",
        "err.archive_empty": "Arxiv ichida fayl yoʻq.",
        "err.too_many_pages": "PDF'da sahifalar juda koʻp.",
        "err.image_too_large": "Surat oʻlchami juda katta.",
        "err.tool_disabled": "Bu amal vaqtincha oʻchirilgan. Keyinroq urinib koʻring.",
        "err.generic": "Xatolik yuz berdi. Birozdan keyin qayta urinib koʻring.",
    },
    "ru": {
        "start": (
            "Здравствуйте! Я бот <b>Universe</b>.\n\n"
            "Пришлите файл: Word, Excel, PowerPoint, PDF, фото или архив. "
            "Я предложу кнопками, что с ним можно сделать.\n\n"
            "Если отправить несколько фото одним альбомом, я соберу из них PDF."
        ),
        "help": (
            "<b>Что я умею</b>\n"
            "• Word, Excel, PowerPoint → PDF\n"
            "• PDF: сжать, разбить на картинки или страницы, объединить\n"
            "• Фото: JPG/PNG/WEBP, сжатие, PDF\n"
            "• Архивы: распаковать, перепаковать в ZIP\n\n"
            "Файлы до {max_mb} МБ. Для больших файлов используйте сайт: {site}\n"
            "После обработки файлы удаляются с сервера.\n\n"
            "/lang — сменить язык"
        ),
        "lang_prompt": "Выберите язык:",
        "lang_set": "Язык изменён: Русский.",
        "choose": "<b>{name}</b>\nЧто сделать?",
        "choose_album": "Файлов: {count}. Что сделать?",
        "unsupported": "Такой файл я пока не обрабатываю. Пришлите Word, Excel, PowerPoint, PDF, фото или архив.",
        "mixed_album": "В альбоме файлы разных типов. Пришлите файлы одного типа, например только фото.",
        "too_big": (
            "Файл {size} МБ, а Telegram даёт ботам открывать файлы только до {max_mb} МБ.\n"
            'Обработайте его на сайте: <a href="{url}">{url}</a>'
        ),
        "working": "⏳ Обрабатываю…",
        "done": "✅ Готово. Файлы удалятся с сервера автоматически.",
        "result_link": '📎 Результат слишком большой для Telegram. Скачайте его здесь (в течение часа): <a href="{url}">скачать</a>',
        "busy": "Предыдущий файл ещё обрабатывается. Подождите, пожалуйста.",
        "more_files": "Ещё {count} файлов не поместились в Telegram. Распакуйте архив на сайте: {site}",
        "expired": "Эта кнопка устарела. Пришлите файл ещё раз.",
        "act.pdf": "📄 В PDF",
        "act.jpg": "🖼 JPG",
        "act.png": "🖼 PNG",
        "act.webp": "🖼 WEBP",
        "act.shrink": "🗜 Сжать",
        "act.split": "✂️ Разбить на страницы",
        "act.merge": "🔗 Объединить",
        "act.extract": "📂 Распаковать",
        "act.zip": "🗂 В ZIP",
        "err.unsupported_format": "Тип файла не подходит для этой операции. Возможно, расширение не совпадает с содержимым.",
        "err.file_too_large": "Файл слишком большой.",
        "err.daily_limit_reached": "Дневной лимит исчерпан. Попробуйте завтра.",
        "err.throttled": "Слишком много запросов. Попробуйте через минуту.",
        "err.corrupt_file": "Не удалось открыть файл: он повреждён или в другом формате.",
        "err.timeout": "Обработка заняла слишком много времени. Попробуйте файл поменьше.",
        "err.malware_detected": "В файле найдена вредоносная программа. Он не обработан и удалён.",
        "err.scan_unavailable": "Не удалось проверить файл на вирусы. Попробуйте чуть позже.",
        "err.pdf_encrypted": "PDF защищён паролем.",
        "err.archive_encrypted": "Архив защищён паролем.",
        "err.wrong_password": "Неверный пароль.",
        "err.archive_too_large": "После распаковки архив получается слишком большим.",
        "err.archive_too_many_files": "В архиве слишком много файлов.",
        "err.archive_empty": "В архиве нет файлов.",
        "err.too_many_pages": "В PDF слишком много страниц.",
        "err.image_too_large": "Слишком большое разрешение изображения.",
        "err.tool_disabled": "Эта операция временно выключена. Попробуйте позже.",
        "err.generic": "Что-то пошло не так. Попробуйте чуть позже.",
    },
    "en": {
        "start": (
            "Hi! I'm the <b>Universe</b> bot.\n\n"
            "Send me a file: Word, Excel, PowerPoint, PDF, a photo or an archive. "
            "I'll offer what I can do with it as buttons.\n\n"
            "Send several photos as one album and I'll turn them into a PDF."
        ),
        "help": (
            "<b>What I can do</b>\n"
            "• Word, Excel, PowerPoint → PDF\n"
            "• PDF: compress, split into images or pages, merge\n"
            "• Photos: JPG/PNG/WEBP, compress, make a PDF\n"
            "• Archives: extract, repack as ZIP\n\n"
            "Files up to {max_mb} MB. For bigger files use the website: {site}\n"
            "Files are deleted from the server after processing.\n\n"
            "/lang — change language"
        ),
        "lang_prompt": "Choose a language:",
        "lang_set": "Language changed: English.",
        "choose": "<b>{name}</b>\nWhat should I do?",
        "choose_album": "{count} files. What should I do?",
        "unsupported": "I can't process this kind of file yet. Send Word, Excel, PowerPoint, PDF, a photo or an archive.",
        "mixed_album": "This album mixes file types. Send files of one kind, for example only photos.",
        "too_big": (
            "This file is {size} MB, and Telegram lets bots open files only up to {max_mb} MB.\n"
            'Process it on the website: <a href="{url}">{url}</a>'
        ),
        "working": "⏳ Working on it…",
        "done": "✅ Done. Files are deleted from the server automatically.",
        "result_link": '📎 The result is too big for Telegram. Download it here (within an hour): <a href="{url}">download</a>',
        "busy": "Your previous file is still being processed. Please wait.",
        "more_files": "{count} more files didn't fit in Telegram. Extract the archive on the website: {site}",
        "expired": "This button has expired. Send the file again.",
        "act.pdf": "📄 Make PDF",
        "act.jpg": "🖼 JPG",
        "act.png": "🖼 PNG",
        "act.webp": "🖼 WEBP",
        "act.shrink": "🗜 Compress",
        "act.split": "✂️ Split into pages",
        "act.merge": "🔗 Merge",
        "act.extract": "📂 Extract",
        "act.zip": "🗂 Repack as ZIP",
        "err.unsupported_format": "This file doesn't fit that action. Its extension may not match its contents.",
        "err.file_too_large": "The file is too large.",
        "err.daily_limit_reached": "You've reached today's limit. Try again tomorrow.",
        "err.throttled": "Too many requests. Try again in a minute.",
        "err.corrupt_file": "Couldn't open the file: it's damaged or in a different format.",
        "err.timeout": "Processing took too long. Try a smaller file.",
        "err.malware_detected": "Malware was found in this file. It wasn't processed and has been deleted.",
        "err.scan_unavailable": "Couldn't scan the file for viruses. Please try again in a moment.",
        "err.pdf_encrypted": "The PDF is password-protected.",
        "err.archive_encrypted": "The archive is password-protected.",
        "err.wrong_password": "That password is wrong.",
        "err.archive_too_large": "This archive unpacks to too much data.",
        "err.archive_too_many_files": "This archive has too many files.",
        "err.archive_empty": "There are no files in this archive.",
        "err.too_many_pages": "The PDF has too many pages.",
        "err.image_too_large": "The image dimensions are too large.",
        "err.tool_disabled": "This action is turned off for now. Please try again later.",
        "err.generic": "Something went wrong. Please try again in a moment.",
    },
}

LANGUAGE_NAMES = {"uz": "🇺🇿 Oʻzbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}


def pick_language(code: str | None) -> str:
    """Telegram's language_code ("ru", "en-US", "uz") -> one of ours."""
    base = (code or "").split("-")[0].lower()
    return base if base in LANGUAGES else DEFAULT


def t(lang: str, key: str, **params: object) -> str:
    table = TEXTS.get(lang, TEXTS[DEFAULT])
    template = table.get(key) or TEXTS[DEFAULT].get(key) or key
    return template.format(**params) if params else template


def error_text(lang: str, code: str) -> str:
    key = f"err.{code}"
    return t(lang, key) if key in TEXTS[DEFAULT] else t(lang, "err.generic")
