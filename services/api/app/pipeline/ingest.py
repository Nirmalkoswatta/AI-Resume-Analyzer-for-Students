import re
from dataclasses import replace
from statistics import median
from typing import Any

import pymupdf

from app.config import Settings
from app.errors import (
    CorruptPdfError,
    EmptyDocumentError,
    EncryptedPdfError,
    NotMachineReadableError,
    TooManyPagesError,
)
from app.pipeline.document import Document, Line, Page, Span
from app.pipeline.layout import (
    count_columns,
    has_running_header_or_footer,
    split_into_columns,
)

FLAG_ITALIC = 1 << 1
FLAG_BOLD = 1 << 4

UNMAPPABLE_GLYPHS = re.compile(r"[-�]")

MAX_LINES_FOR_TABLE_DETECTION = 300
ROW_TOLERANCE_RATIO = 0.6

pymupdf.no_recommend_layout()


def parse_document(payload: bytes, settings: Settings) -> Document:
    with open_pdf(payload) as pdf:
        if pdf.page_count > settings.max_page_count:
            raise TooManyPagesError
        if pdf.page_count == 0:
            raise EmptyDocumentError

        pages = build_pages(pdf)

    require_machine_readable(pages, settings)

    return Document(
        pages=pages,
        font_families=collect_font_families(pages),
        column_count=max(count_columns(page.lines, page.width, page.height) for page in pages),
        has_text_in_header_footer=has_running_header_or_footer(pages),
    )


def open_pdf(payload: bytes) -> pymupdf.Document:
    try:
        pdf = pymupdf.open(stream=payload, filetype="pdf")
    except Exception as error:
        raise CorruptPdfError from error

    if pdf.needs_pass or pdf.is_encrypted:
        pdf.close()
        raise EncryptedPdfError

    return pdf


def build_pages(pdf: pymupdf.Document) -> tuple[Page, ...]:
    pages: list[Page] = []
    line_index = 0

    for page_number, source in enumerate(pdf, start=1):
        placed: list[Line] = []
        for raw_line in iter_raw_lines(source):
            line = build_line(raw_line, page_number)
            if line is None:
                continue
            placed.append(line)

        lines: list[Line] = []
        column_starts: list[int] = []
        for column in read_in_column_order(placed, source.rect.width, source.rect.height):
            if lines:
                column_starts.append(line_index)
            for line in column:
                lines.append(replace(line, index=line_index))
                line_index += 1

        pages.append(
            Page(
                number=page_number,
                width=source.rect.width,
                height=source.rect.height,
                lines=tuple(lines),
                column_start_indices=tuple(column_starts),
                image_count=len(source.get_images(full=True)),
                table_count=count_tables(source, len(lines)),
                character_count=len(source.get_text().strip()),
            )
        )

    return tuple(pages)


def iter_raw_lines(source: pymupdf.Page) -> list[dict[str, Any]]:
    content: dict[str, Any] = source.get_text("dict")
    return [
        raw_line
        for block in content["blocks"]
        if block.get("type") == 0
        for raw_line in block.get("lines", [])
    ]


def read_in_column_order(lines: list[Line], width: float, height: float) -> list[list[Line]]:
    if not lines:
        return []

    columns = split_into_columns(tuple(lines), width, height)
    return [order_within_column(column) for column in columns]


def order_within_column(lines: list[Line]) -> list[Line]:
    if not lines:
        return []

    tolerance = row_tolerance(lines)
    rows: list[list[Line]] = []

    for line in sorted(lines, key=lambda item: (item.top, item.x0)):
        if rows and line.top - rows[-1][0].top <= tolerance:
            rows[-1].append(line)
        else:
            rows.append([line])

    return [line for row in rows for line in sorted(row, key=lambda item: item.x0)]


def row_tolerance(lines: list[Line]) -> float:
    heights = [line.bottom - line.top for line in lines if line.bottom > line.top]
    if not heights:
        return 0.0
    return median(heights) * ROW_TOLERANCE_RATIO


def build_line(raw_line: dict[str, Any], page_number: int) -> Line | None:
    spans = tuple(build_span(raw_span) for raw_span in raw_line.get("spans", []))
    if not spans or not "".join(span.text for span in spans).strip():
        return None

    x0, top, x1, bottom = raw_line["bbox"]
    return Line(
        index=0,
        page_number=page_number,
        spans=spans,
        x0=float(x0),
        top=float(top),
        x1=float(x1),
        bottom=float(bottom),
    )


def build_span(raw_span: dict[str, Any]) -> Span:
    x0, top, x1, bottom = raw_span["bbox"]
    flags = int(raw_span.get("flags", 0))
    font = str(raw_span.get("font", ""))

    return Span(
        text=drop_unmappable_glyphs(str(raw_span.get("text", ""))),
        font=font,
        size=float(raw_span.get("size", 0.0)),
        bold=bool(flags & FLAG_BOLD) or "bold" in font.lower(),
        italic=bool(flags & FLAG_ITALIC) or "italic" in font.lower(),
        x0=float(x0),
        top=float(top),
        x1=float(x1),
        bottom=float(bottom),
    )


def drop_unmappable_glyphs(text: str) -> str:
    return UNMAPPABLE_GLYPHS.sub("", text)


def count_tables(source: pymupdf.Page, line_count: int) -> int:
    if line_count > MAX_LINES_FOR_TABLE_DETECTION:
        return 0

    try:
        return len(source.find_tables().tables)
    except Exception:
        return 0


def collect_font_families(pages: tuple[Page, ...]) -> tuple[str, ...]:
    families = {
        normalise_font_name(span.font)
        for page in pages
        for line in page.lines
        for span in line.spans
        if span.font
    }
    return tuple(sorted(families))


def normalise_font_name(font: str) -> str:
    without_subset = font.split("+", 1)[-1]
    return without_subset.split("-", 1)[0].split(",", 1)[0]


def require_machine_readable(pages: tuple[Page, ...], settings: Settings) -> None:
    if not pages:
        raise EmptyDocumentError

    total_characters = sum(page.character_count for page in pages)
    if total_characters == 0:
        raise NotMachineReadableError

    threshold = settings.min_characters_per_page * len(pages)
    if total_characters < threshold:
        raise NotMachineReadableError
