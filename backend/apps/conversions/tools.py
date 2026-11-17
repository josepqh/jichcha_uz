"""Tool registry: what each tool accepts, its options and the processor that runs it."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rest_framework import serializers

from .formats import (
    ARCHIVE_INPUTS,
    IMAGE_INPUTS,
    IMAGE_OUTPUTS,
    OFFICE_INPUTS,
    PDF_INPUTS,
)
from .processors import archives, images, office, pdf
from .processors.base import InputFile, OutputFile

Processor = Callable[[list[InputFile], dict, Path], list[OutputFile]]


class ConvertImageOptions(serializers.Serializer):
    target = serializers.ChoiceField(choices=IMAGE_OUTPUTS)
    quality = serializers.IntegerField(min_value=1, max_value=100, required=False)


class CompressImageOptions(serializers.Serializer):
    level = serializers.ChoiceField(choices=list(images.COMPRESS_LEVELS), default="medium")
    quality = serializers.IntegerField(min_value=1, max_value=100, required=False)


class ImagesToPdfOptions(serializers.Serializer):
    page_size = serializers.ChoiceField(choices=list(images.PAGE_SIZES_PT), default="a4")
    orientation = serializers.ChoiceField(choices=["auto", "portrait", "landscape"], default="auto")
    margin = serializers.ChoiceField(choices=list(images.MARGINS_MM), default="small")


class NoOptions(serializers.Serializer):
    pass


_RANGES = re.compile(r"^\s*\d+\s*(-\s*\d*\s*)?(,\s*\d+\s*(-\s*\d*\s*)?)*,?\s*$")


class SplitPdfOptions(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["each", "ranges"], default="each")
    ranges = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")

    def validate(self, attrs: dict) -> dict:
        if attrs["mode"] == "ranges" and not _RANGES.match(attrs.get("ranges", "")):
            raise serializers.ValidationError({"ranges": ["Use page numbers and ranges like 1-3, 5, 8-10."]})
        return attrs


class PageSpec(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, max_value=pdf.MAX_PAGES)
    rotate = serializers.ChoiceField(choices=[0, 90, 180, 270], default=0)


class OrganizePdfOptions(serializers.Serializer):
    pages = serializers.ListField(child=PageSpec(), min_length=1, max_length=pdf.MAX_PAGES)


class CompressPdfOptions(serializers.Serializer):
    level = serializers.ChoiceField(choices=list(pdf.PDF_COMPRESS_LEVELS), default="medium")


class PdfToImagesOptions(serializers.Serializer):
    format = serializers.ChoiceField(choices=["jpg", "png"], default="jpg")
    quality = serializers.ChoiceField(choices=list(pdf.RENDER_DPI), default="medium")


class CropBox(serializers.Serializer):
    """A crop as fractions of the (EXIF-upright) image, so it doesn't depend on preview size."""

    x = serializers.FloatField(min_value=0, max_value=1)
    y = serializers.FloatField(min_value=0, max_value=1)
    w = serializers.FloatField(min_value=0.005, max_value=1)
    h = serializers.FloatField(min_value=0.005, max_value=1)

    def validate(self, attrs: dict) -> dict:
        if attrs["x"] + attrs["w"] > 1.001 or attrs["y"] + attrs["h"] > 1.001:
            raise serializers.ValidationError("The crop must stay inside the image.")
        return attrs


class EditImageOptions(serializers.Serializer):
    crop = CropBox(required=False)
    aspect = serializers.ChoiceField(choices=list(images.ASPECTS), default="free")
    rotate = serializers.ChoiceField(choices=[0, 90, 180, 270], default=0)
    flip = serializers.ChoiceField(choices=["none", "horizontal", "vertical"], default="none")
    resize = serializers.ChoiceField(choices=["none", "percent", "pixels"], default="none")
    percent = serializers.IntegerField(min_value=1, max_value=400, default=100)
    width = serializers.IntegerField(min_value=1, max_value=images.MAX_EDGE, required=False, allow_null=True)
    height = serializers.IntegerField(min_value=1, max_value=images.MAX_EDGE, required=False, allow_null=True)
    format = serializers.ChoiceField(choices=list(images.EDIT_FORMATS), default="keep")

    def validate(self, attrs: dict) -> dict:
        if attrs["resize"] == "pixels" and not (attrs.get("width") or attrs.get("height")):
            raise serializers.ValidationError({"width": ["Give a width, a height or both."]})
        return attrs


class CreateArchiveOptions(serializers.Serializer):
    format = serializers.ChoiceField(choices=["zip", "7z"], default="zip")


_PASSWORD = {"max_length": 256, "trim_whitespace": False, "write_only": True}


class ExtractArchiveOptions(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True, **_PASSWORD)


class RepackArchiveOptions(serializers.Serializer):
    target = serializers.ChoiceField(choices=["zip", "7z"], default="zip")
    password = serializers.CharField(required=False, allow_blank=True, **_PASSWORD)


class UnlockPdfOptions(serializers.Serializer):
    password = serializers.CharField(**_PASSWORD)


@dataclass(frozen=True)
class Tool:
    slug: str
    category: str
    accepts: frozenset[str]
    outputs: tuple[str, ...]
    options: type[serializers.Serializer]
    run: Processor
    # Upper bound regardless of policy (None = role's max_batch).
    max_files: int | None = None
    min_files: int = 1
    # Celery queue: heavy engines (LibreOffice) run on their own workers.
    queue: str = "light"
    time_limit: int = 120
    # Takes any file at all (packing into an archive); content is still never executed.
    accepts_any: bool = False
    # Also offer every output in one zip. Off for extraction: the user already has the archive,
    # and a second copy would double the disk an archive bomb-sized upload can take.
    bundle: bool = True


TOOLS: dict[str, Tool] = {
    tool.slug: tool
    for tool in (
        Tool(
            slug="image-convert",
            category="image",
            accepts=IMAGE_INPUTS,
            outputs=IMAGE_OUTPUTS,
            options=ConvertImageOptions,
            run=images.convert_images,
        ),
        Tool(
            slug="image-edit",
            category="image",
            accepts=IMAGE_INPUTS,
            outputs=("jpg", "png", "webp", "avif", "gif"),
            options=EditImageOptions,
            run=images.edit_images,
        ),
        Tool(
            slug="image-compress",
            category="compress",
            accepts=IMAGE_INPUTS,
            outputs=("jpg", "png", "webp", "avif", "gif"),
            options=CompressImageOptions,
            run=images.compress_images,
        ),
        Tool(
            slug="images-to-pdf",
            category="pdf",
            accepts=IMAGE_INPUTS,
            outputs=("pdf",),
            options=ImagesToPdfOptions,
            run=images.images_to_pdf,
            max_files=100,
        ),
        Tool(
            slug="office-to-pdf",
            category="office",
            accepts=OFFICE_INPUTS,
            outputs=("pdf",),
            options=NoOptions,
            run=office.office_to_pdf,
            max_files=10,
            queue="office",
            time_limit=300,
        ),
        Tool(
            slug="pdf-merge",
            category="pdf",
            accepts=PDF_INPUTS,
            outputs=("pdf",),
            options=NoOptions,
            run=pdf.merge_pdfs,
            min_files=2,
            max_files=50,
        ),
        Tool(
            slug="pdf-split",
            category="pdf",
            accepts=PDF_INPUTS,
            outputs=("pdf",),
            options=SplitPdfOptions,
            run=pdf.split_pdf,
            max_files=1,
        ),
        Tool(
            slug="pdf-organize",
            category="pdf",
            accepts=PDF_INPUTS,
            outputs=("pdf",),
            options=OrganizePdfOptions,
            run=pdf.organize_pdf,
            max_files=1,
        ),
        Tool(
            slug="pdf-compress",
            category="compress",
            accepts=PDF_INPUTS,
            outputs=("pdf",),
            options=CompressPdfOptions,
            run=pdf.compress_pdf,
            max_files=10,
        ),
        Tool(
            slug="pdf-to-images",
            category="pdf",
            accepts=PDF_INPUTS,
            outputs=("jpg", "png"),
            options=PdfToImagesOptions,
            run=pdf.pdf_to_images,
            max_files=1,
            time_limit=240,
        ),
        Tool(
            slug="pdf-unlock",
            category="pdf",
            accepts=PDF_INPUTS,
            outputs=("pdf",),
            options=UnlockPdfOptions,
            run=pdf.unlock_pdf,
            max_files=1,
        ),
        Tool(
            slug="archive-extract",
            category="archive",
            accepts=ARCHIVE_INPUTS,
            outputs=(),
            options=ExtractArchiveOptions,
            run=archives.extract,
            max_files=1,
            time_limit=300,
            bundle=False,
        ),
        Tool(
            slug="archive-create",
            category="archive",
            accepts=frozenset(),
            accepts_any=True,
            outputs=("zip", "7z"),
            options=CreateArchiveOptions,
            run=archives.create,
            time_limit=300,
        ),
        Tool(
            slug="archive-convert",
            category="archive",
            accepts=ARCHIVE_INPUTS,
            outputs=("zip", "7z"),
            options=RepackArchiveOptions,
            run=archives.repack,
            max_files=5,
            time_limit=300,
        ),
    )
}


def get_tool(slug: str) -> Tool | None:
    return TOOLS.get(slug)
