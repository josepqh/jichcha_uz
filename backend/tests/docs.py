"""Builders for small, real PDF and Office files used in tests."""

import io
import zipfile

import img2pdf
import pikepdf
from PIL import Image


def pdf_bytes(pages: int = 3, size=(400, 300), quality: int = 90, noise: bool = False) -> bytes:
    images = []
    for i in range(pages):
        if noise:
            img = Image.effect_noise(size, 70).convert("RGB")
        else:
            img = Image.new("RGB", size, (40 * i % 255, 120, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        images.append(buf.getvalue())
    return img2pdf.convert(images)


def encrypted_pdf_bytes() -> bytes:
    with pikepdf.open(io.BytesIO(pdf_bytes(1))) as pdf:
        out = io.BytesIO()
        pdf.save(out, encryption=pikepdf.Encryption(owner="owner-pass", user="user-pass"))
        return out.getvalue()


def docx_bytes(text: str = "Salom, dunyo! Oʻzbekcha matn: gʻalaba, ҳаёт.") -> bytes:
    """Smallest valid DOCX that Word and LibreOffice open."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
    return buf.getvalue()


def docx_including_file(target_path: str) -> bytes:
    """Attack sample: a Word INCLUDETEXT field that pulls a server-side file into the document."""
    body = (
        "<w:p><w:r><w:t>Before</w:t></w:r></w:p>"
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> INCLUDETEXT "{target_path}" </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "<w:r><w:t>placeholder</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        "</w:p>"
        "<w:p><w:r><w:t>After</w:t></w:r></w:p>"
    )
    raw = docx_bytes("x")
    src = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f"<w:body>{body}</w:body></w:document>"
                ).encode()
            zf.writestr(item, data)
    return out.getvalue()


def odt_linking_file(target_path: str) -> bytes:
    """Attack sample: an ODT linked section whose source is a server-side file."""
    from pathlib import Path

    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" office:version="1.3">'
        "<office:body><office:text>"
        "<text:p>Before</text:p>"
        '<text:section text:name="S1">'
        f'<text:section-source xlink:href="{Path(target_path).as_uri()}" xlink:type="simple" text:filter-name="Text"/>'
        "<text:p>placeholder</text:p></text:section>"
        "<text:p>After</text:p>"
        "</office:text></office:body></office:document-content>"
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
        '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml", content, zipfile.ZIP_DEFLATED)
        zf.writestr("META-INF/manifest.xml", manifest, zipfile.ZIP_DEFLATED)
    return out.getvalue()


# --- Archives -------------------------------------------------------------------------------------


def zip_bytes(entries: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return out.getvalue()


def zip_with_cp866_name(text: str, data: bytes = b"hello") -> bytes:
    """A zip as Windows Explorer makes it: Cyrillic name in CP866, no UTF-8 flag."""
    raw = text.encode("cp866")
    placeholder = "X" * len(raw)
    blob = zip_bytes({placeholder: data})
    assert blob.count(placeholder.encode()) == 2  # local and central headers
    return blob.replace(placeholder.encode(), raw)


def tar_bytes(entries: dict[str, bytes], mode: str = "w", symlinks: dict[str, str] | None = None) -> bytes:
    import tarfile

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode=mode) as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        for name, target in (symlinks or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tf.addfile(info)
    return out.getvalue()


def libarchive_bytes(fmt: str, entries: dict[str, bytes], **kwargs) -> bytes:
    import tempfile
    from pathlib import Path

    import libarchive

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"a.{fmt}"
        with libarchive.file_writer(str(path), fmt, **kwargs) as archive:
            for name, data in entries.items():
                archive.add_file_from_memory(name, len(data), data)
        return path.read_bytes()


def rar4_bytes(entries: dict[str, bytes]) -> bytes:
    """Minimal RAR 4 archive with stored (uncompressed) ASCII-named files, built from the spec."""
    import struct
    import zlib

    def block(head_type: int, flags: int, body: bytes) -> bytes:
        header = struct.pack("<BHH", head_type, flags, 7 + len(body)) + body
        return struct.pack("<H", zlib.crc32(header) & 0xFFFF) + header

    out = b"Rar!\x1a\x07\x00" + block(0x73, 0, b"\x00" * 6)
    for name, data in entries.items():
        raw = name.replace("/", "\\").encode("ascii")
        body = struct.pack(
            "<IIBIIBBHI", len(data), len(data), 2, zlib.crc32(data), 0x5A210000, 20, 0x30, len(raw), 0x20
        )
        out += block(0x74, 0x8000, body + raw) + data
    return out + block(0x7B, 0x4000, b"")
