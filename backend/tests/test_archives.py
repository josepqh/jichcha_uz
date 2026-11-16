import bz2
import gzip
import io
import lzma
import zipfile

import libarchive
import pytest

from apps.conversions.formats import detect_file
from apps.conversions.processors import archives
from apps.conversions.processors.base import InputFile, ProcessingError, safe_relpath
from tests.docs import (
    epub_bytes,
    fb2_bytes,
    libarchive_bytes,
    pdf_bytes,
    rar4_bytes,
    tar_bytes,
    zip_bytes,
    zip_with_cp866_name,
)


def write(tmp_path, name: str, data: bytes, fmt: str) -> InputFile:
    path = tmp_path / f"src-{name}"
    path.write_bytes(data)
    return InputFile(path=path, name=name, fmt=fmt)


def extracted(tmp_path, name, data, fmt) -> dict[str, bytes]:
    files = archives.extract_archive(write(tmp_path, name, data, fmt), tmp_path / "x")
    return {f.name: f.path.read_bytes() for f in files}


def read_zip(path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {i.filename: zf.read(i) for i in zf.infolist()}


def read_any(path) -> dict[str, bytes]:
    with libarchive.file_reader(str(path)) as archive:
        return {e.pathname: b"".join(e.get_blocks()) for e in archive if e.isreg}


class TestDetection:
    @pytest.mark.parametrize(
        ("data", "fmt"),
        [
            (zip_bytes({"a.txt": b"x"}), "zip"),
            # A zip that stores a PDF uncompressed has "%PDF-" in its first kilobyte; it is still a zip.
            (zip_bytes({"a.pdf": pdf_bytes(1)}, zipfile.ZIP_STORED), "zip"),
            (rar4_bytes({"a.txt": b"x"}), "rar"),
            (libarchive_bytes("7zip", {"a.txt": b"x"}), "7z"),
            (tar_bytes({"a.txt": b"x"}), "tar"),
            (tar_bytes({"a.pdf": pdf_bytes(1)}), "tar"),
            (gzip.compress(b"hello"), "gz"),
            (bz2.compress(b"hello"), "bz2"),
            (lzma.compress(b"hello"), "xz"),
            (epub_bytes([("Bob", "Matn")]), "epub"),
            (fb2_bytes("Matn"), "fb2"),
        ],
    )
    def test_formats_by_content(self, data, fmt):
        detected = detect_file(io.BytesIO(data), "renamed.bin")
        assert detected is not None and detected.fmt == fmt

    def test_mobi_and_azw3_share_a_container(self):
        mobi = b"\x00" * 60 + b"BOOKMOBI" + b"\x00" * 100
        assert detect_file(io.BytesIO(mobi), "a.mobi").fmt == "mobi"
        assert detect_file(io.BytesIO(mobi), "a.azw3").fmt == "azw3"


class TestSafeRelpath:
    @pytest.mark.parametrize(
        ("raw", "clean"),
        [
            ("../../etc/passwd", "etc/passwd"),
            ("/abs/path/file.txt", "abs/path/file.txt"),
            ("C:\\Users\\a\\..\\b.txt", "C_/Users/a/b.txt"),
            ("./ok/./x.txt", "ok/x.txt"),
            ("..", "file"),
            ("papka/oʻzbek.txt", "papka/oʻzbek.txt"),
        ],
    )
    def test_cleans_paths(self, raw, clean):
        assert safe_relpath(raw) == clean


class TestExtract:
    def test_zip_keeps_folders_and_unicode_names(self, tmp_path):
        data = zip_bytes({"papka/oʻzbek.txt": b"salom", "b.txt": b"x", "papka/ichki/": b""})
        assert extracted(tmp_path, "a.zip", data, "zip") == {"papka/oʻzbek.txt": b"salom", "b.txt": b"x"}

    def test_windows_cp866_names(self, tmp_path):
        assert list(extracted(tmp_path, "a.zip", zip_with_cp866_name("Отчёт.txt"), "zip")) == ["Отчёт.txt"]

    @pytest.mark.parametrize(
        ("name", "data", "fmt"),
        [
            ("a.rar", rar4_bytes({"papka/a.txt": b"one", "b.txt": b"two"}), "rar"),
            ("a.7z", libarchive_bytes("7zip", {"papka/a.txt": b"one", "b.txt": b"two"}), "7z"),
            ("a.tar.gz", tar_bytes({"papka/a.txt": b"one", "b.txt": b"two"}, "w:gz"), "gz"),
            ("a.tar.xz", tar_bytes({"papka/a.txt": b"one", "b.txt": b"two"}, "w:xz"), "xz"),
        ],
    )
    def test_other_formats(self, tmp_path, name, data, fmt):
        assert extracted(tmp_path, name, data, fmt) == {"papka/a.txt": b"one", "b.txt": b"two"}

    @pytest.mark.parametrize(
        ("name", "data", "fmt"),
        [("hisobot.txt.gz", gzip.compress(b"hello"), "gz"), ("hisobot.txt.bz2", bz2.compress(b"hello"), "bz2")],
    )
    def test_single_compressed_file(self, tmp_path, name, data, fmt):
        assert extracted(tmp_path, name, data, fmt) == {"hisobot.txt": b"hello"}

    def test_traversal_names_stay_inside(self, tmp_path):
        data = zip_bytes({"../../evil.txt": b"a", "/etc/cron.d/x": b"b", "ok/../../../c.txt": b"c"})
        out = extracted(tmp_path, "a.zip", data, "zip")
        assert out == {"evil.txt": b"a", "etc/cron.d/x": b"b", "ok/c.txt": b"c"}
        written = {p.name for p in (tmp_path / "x").iterdir()}
        assert written == {"00000", "00001", "00002"}  # numbered files only
        assert not (tmp_path.parent / "evil.txt").exists()

    def test_symlinks_are_skipped(self, tmp_path):
        data = tar_bytes({"a.txt": b"x"}, symlinks={"secret": "/etc/passwd"})
        assert extracted(tmp_path, "a.tar", data, "tar") == {"a.txt": b"x"}

    def test_bomb_stops_at_the_unpacked_limit(self, tmp_path, settings):
        settings.ARCHIVE_MAX_UNPACKED_MB = 1
        bomb = zip_bytes({"zeros.bin": b"\0" * (20 * 1024 * 1024)})
        assert len(bomb) < 100_000
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "bomb.zip", bomb, "zip")
        assert exc.value.code == "archive_too_large"
        written = sum(p.stat().st_size for p in (tmp_path / "x").iterdir())
        assert written <= 1024 * 1024 + 64 * 1024  # stopped within one block of the limit

    def test_too_many_entries(self, tmp_path, settings):
        settings.ARCHIVE_MAX_ENTRIES = 5
        data = zip_bytes({f"{i}.txt": b"x" for i in range(6)})
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "a.zip", data, "zip")
        assert exc.value.code == "archive_too_many_files"

    def test_too_many_folders(self, tmp_path, settings):
        settings.ARCHIVE_MAX_ENTRIES = 5
        data = zip_bytes({f"d{i}/": b"" for i in range(21)} | {"a.txt": b"x"})
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "a.zip", data, "zip")
        assert exc.value.code == "archive_too_many_files"

    def test_encrypted(self, tmp_path):
        data = libarchive_bytes("zip", {"a.txt": b"secret"}, passphrase="pw", options="encryption=zipcrypt")
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "a.zip", data, "zip")
        assert exc.value.code == "archive_encrypted"

    def test_empty_and_corrupt(self, tmp_path):
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "a.zip", zip_bytes({"dir/": b""}), "zip")
        assert exc.value.code == "archive_empty"
        with pytest.raises(ProcessingError) as exc:
            extracted(tmp_path, "b.rar", b"Rar!\x1a\x07\x00" + b"\xff" * 50, "rar")
        assert exc.value.code == "corrupt_file"


class TestCreateAndRepack:
    def test_create_zip_from_any_files(self, tmp_path):
        inputs = [
            write(tmp_path, "rasm.png", b"\x89PNG fake", "bin"),
            write(tmp_path, "dastur.exe", b"MZ\x90\x00", "bin"),
            InputFile(path=write(tmp_path, "x", b"second", "bin").path, name="rasm.png", fmt="bin"),
        ]
        [out] = archives.create(inputs, {"format": "zip"}, tmp_path)
        assert out.name == "archive.zip"
        assert read_zip(out.path) == {
            "rasm.png": b"\x89PNG fake",
            "dastur.exe": b"MZ\x90\x00",
            "rasm (2).png": b"second",
        }

    def test_create_7z_single_file_keeps_its_name(self, tmp_path):
        [out] = archives.create([write(tmp_path, "hisobot.docx", b"data", "bin")], {"format": "7z"}, tmp_path)
        assert out.name == "hisobot.7z"
        assert read_any(out.path) == {"hisobot.docx": b"data"}

    def test_rar_to_zip_keeps_structure(self, tmp_path):
        src = write(tmp_path, "arxiv.rar", rar4_bytes({"papka/a.txt": b"one", "b.txt": b"two"}), "rar")
        [out] = archives.repack([src], {"target": "zip"}, tmp_path)
        assert out.name == "arxiv.zip"
        assert read_zip(out.path) == {"papka/a.txt": b"one", "b.txt": b"two"}

    def test_tar_gz_to_7z_names(self, tmp_path):
        src = write(tmp_path, "backup.tar.gz", tar_bytes({"a.txt": b"x"}, "w:gz"), "gz")
        [out] = archives.repack([src], {"target": "7z"}, tmp_path)
        assert out.name == "backup.7z"
        assert read_any(out.path) == {"a.txt": b"x"}
