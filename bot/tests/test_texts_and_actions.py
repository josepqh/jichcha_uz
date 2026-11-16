import re

import pytest

from universe_bot.actions import ACTIONS, ALBUM_ACTIONS, WEB_TOOL, actions_for, family_of
from universe_bot.texts import LANGUAGES, TEXTS, error_text, pick_language, t


def test_every_language_has_every_key():
    keys = set(TEXTS["uz"])
    for lang in LANGUAGES:
        assert set(TEXTS[lang]) == keys, lang


def test_placeholders_match_across_languages():
    def fields(text: str) -> set[str]:
        return set(re.findall(r"{(\w+)}", text))

    for key, text in TEXTS["uz"].items():
        for lang in LANGUAGES:
            assert fields(TEXTS[lang][key]) == fields(text), f"{lang}:{key}"


def test_html_tags_are_balanced():
    for lang in LANGUAGES:
        for key, text in TEXTS[lang].items():
            for tag in ("b", "a"):
                assert text.count(f"<{tag}") == text.count(f"</{tag}>"), f"{lang}:{key}"


def test_every_action_has_a_button_label():
    keys = {a.key for group in (*ACTIONS.values(), *ALBUM_ACTIONS.values()) for a in group}
    for lang in LANGUAGES:
        for key in keys:
            assert f"act.{key}" in TEXTS[lang]


def test_every_family_has_a_web_fallback():
    assert set(WEB_TOOL) == set(ACTIONS)


@pytest.mark.parametrize(
    ("name", "mime", "family"),
    [
        ("Referat.DOCX", "", "word"),
        ("hisobot.xlsx", "", "excel"),
        ("slayd.pptx", "", "powerpoint"),
        ("scan.pdf", "", "pdf"),
        ("IMG_1234.HEIC", "", "image"),
        ("photo", "image/jpeg", "image"),
        ("kitob.fb2", "", "ebook"),
        ("eslatma.md", "", "text"),
        ("notes.txt", "text/plain", "text"),
        ("arxiv.tar.gz", "", "archive"),
        ("noext", "application/pdf", "pdf"),
        ("dastur.exe", "application/x-msdownload", None),
    ],
)
def test_family_of(name, mime, family):
    assert family_of(name, mime) == family


def test_no_same_format_conversion():
    assert "jpg" not in [a.key for a in actions_for("image", "photo.jpeg")]
    assert "epub" not in [a.key for a in actions_for("ebook", "kitob.epub")]


def test_language_and_errors():
    assert pick_language("ru-RU") == "ru"
    assert pick_language(None) == "uz"
    assert error_text("en", "malware_detected").startswith("Malware")
    assert error_text("ru", "brand_new_code") == t("ru", "err.generic")
