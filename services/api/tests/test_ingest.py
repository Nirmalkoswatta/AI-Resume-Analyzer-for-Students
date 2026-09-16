from types import SimpleNamespace

import pytest

from app.config import Settings
from app.errors import (
    CorruptPdfError,
    EmptyDocumentError,
    EncryptedPdfError,
    NotMachineReadableError,
    TooManyPagesError,
)
from app.pipeline.ingest import (
    MAX_LINES_FOR_TABLE_DETECTION,
    count_tables,
    normalise_font_name,
    parse_document,
)


def test_extracts_text_and_geometry(sample_resume: bytes, settings: Settings) -> None:
    document = parse_document(sample_resume, settings)

    assert document.page_count == 1
    assert document.word_count > 40
    assert document.character_count > 0
    assert "Priya Fernando" in document.lines[0].text


def test_lines_carry_font_metadata(single_column_pdf: bytes, settings: Settings) -> None:
    document = parse_document(single_column_pdf, settings)
    heading = next(line for line in document.lines if line.text == "EDUCATION")

    assert heading.is_upper_case
    assert heading.max_font_size > document.median_font_size
    assert heading.page_number == 1


def test_line_indexes_are_unique_and_ordered(single_column_pdf: bytes, settings: Settings) -> None:
    document = parse_document(single_column_pdf, settings)
    indexes = [line.index for line in document.lines]

    assert indexes == sorted(indexes)
    assert len(indexes) == len(set(indexes))


def test_detects_single_column(single_column_pdf: bytes, settings: Settings) -> None:
    assert parse_document(single_column_pdf, settings).column_count == 1


def test_detects_two_columns(two_column_pdf: bytes, settings: Settings) -> None:
    assert parse_document(two_column_pdf, settings).column_count == 2


def test_detects_a_header_repeated_across_pages(
    header_footer_pdf: bytes, settings: Settings
) -> None:
    assert parse_document(header_footer_pdf, settings).has_text_in_header_footer is True


def test_single_page_never_has_running_furniture(edge_text_pdf: bytes, settings: Settings) -> None:
    assert parse_document(edge_text_pdf, settings).has_text_in_header_footer is False


def test_body_only_resume_has_no_header_text(single_column_pdf: bytes, settings: Settings) -> None:
    assert parse_document(single_column_pdf, settings).has_text_in_header_footer is False


def test_scanned_resume_is_rejected(scanned_pdf: bytes, settings: Settings) -> None:
    with pytest.raises(NotMachineReadableError):
        parse_document(scanned_pdf, settings)


def test_encrypted_resume_is_rejected(encrypted_pdf: bytes, settings: Settings) -> None:
    with pytest.raises(EncryptedPdfError):
        parse_document(encrypted_pdf, settings)


def test_long_document_is_rejected(twelve_page_pdf: bytes, settings: Settings) -> None:
    with pytest.raises(TooManyPagesError):
        parse_document(twelve_page_pdf, settings)


def test_corrupt_payload_is_rejected(settings: Settings) -> None:
    with pytest.raises(CorruptPdfError):
        parse_document(b"%PDF-1.4 this is not a real pdf body", settings)


def test_pdf_without_pages_is_rejected(settings: Settings) -> None:
    empty = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
        b"%%EOF\n"
    )

    with pytest.raises((EmptyDocumentError, CorruptPdfError)):
        parse_document(empty, settings)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ABCDEF+Calibri-Bold", "Calibri"),
        ("Helvetica", "Helvetica"),
        ("Arial,Bold", "Arial"),
        ("XYZABC+TimesNewRoman", "TimesNewRoman"),
    ],
)
def test_font_names_are_normalised(raw: str, expected: str) -> None:
    assert normalise_font_name(raw) == expected


def test_multi_page_resume_is_read_whole(two_page_pdf: bytes, settings: Settings) -> None:
    document = parse_document(two_page_pdf, settings)

    assert document.page_count == 2
    assert document.word_count == sum(
        line.word_count for page in document.pages for line in page.lines
    )
    assert {page.number for page in document.pages} == {1, 2}


def test_line_indexes_continue_across_pages(two_page_pdf: bytes, settings: Settings) -> None:
    document = parse_document(two_page_pdf, settings)
    indexes = [line.index for line in document.lines]
    pages = [line.page_number for line in document.lines]

    assert indexes == sorted(indexes)
    assert len(indexes) == len(set(indexes))
    assert pages == sorted(pages)


def test_every_line_is_reachable_by_index(two_page_pdf: bytes, settings: Settings) -> None:
    document = parse_document(two_page_pdf, settings)

    assert all(document.line_at(line.index) is line for line in document.lines)


class RecordingPage:
    def __init__(self, table_count: int) -> None:
        self.calls = 0
        self.table_count = table_count

    def find_tables(self) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(tables=list(range(self.table_count)))


def test_tables_are_detected_on_a_normal_page() -> None:
    page = RecordingPage(table_count=2)

    assert count_tables(page, line_count=50) == 2
    assert page.calls == 1


def test_table_detection_is_skipped_on_pathological_pages() -> None:
    page = RecordingPage(table_count=2)

    assert count_tables(page, line_count=MAX_LINES_FOR_TABLE_DETECTION + 1) == 0
    assert page.calls == 0


def test_table_detection_failures_are_swallowed() -> None:
    class ExplodingPage:
        def find_tables(self) -> SimpleNamespace:
            raise RuntimeError("mupdf blew up")

    assert count_tables(ExplodingPage(), line_count=10) == 0


def test_lines_are_ordered_visually_not_by_block_order(
    scrambled_order_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(scrambled_order_pdf, settings)
    tops = [line.top for line in document.lines]

    assert tops == sorted(tops)
    assert document.lines[0].text == "Priya Fernando"
