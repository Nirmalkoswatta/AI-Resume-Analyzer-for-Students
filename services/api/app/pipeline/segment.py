from dataclasses import dataclass

from app.pipeline.document import Document, Line
from app.pipeline.lexicon import get_heading_lexicon
from app.schemas.analysis import DetectedSection, TextLocation
from app.schemas.enums import SectionKind

MAX_HEADING_WORDS = 6
LARGE_FONT_RATIO = 1.15
HEADING_FONT_RATIO = 1.25
TITLE_FONT_RATIO = 2.0
MIN_TYPOGRAPHIC_SIGNALS = 1
EXCERPT_MAX_CHARS = 200
MIN_UNLABELLED_SECTION_WORDS = 10


@dataclass(frozen=True)
class Heading:
    line: Line
    kind: SectionKind


@dataclass(frozen=True)
class SectionStart:
    boundary: int
    body_start: int
    kind: SectionKind
    heading: str | None


def segment(document: Document) -> tuple[list[DetectedSection], list[SectionKind]]:
    headings = find_headings(document)
    sections = build_sections(document, headings)
    found = {section.kind for section in sections}
    missing = [kind for kind in get_heading_lexicon().expected_sections if kind not in found]
    return sections, missing


def find_headings(document: Document) -> list[Heading]:
    lexicon = get_heading_lexicon()
    headings: list[Heading] = []

    for line in document.lines:
        if line.word_count == 0 or line.word_count > MAX_HEADING_WORDS:
            continue

        known_kind = lexicon.kind_for(line.text)
        if known_kind is not None:
            headings.append(Heading(line=line, kind=known_kind))
            continue

        if looks_like_heading(line, document.median_font_size):
            headings.append(Heading(line=line, kind=SectionKind.OTHER))

    return headings


def looks_like_heading(line: Line, median_font_size: float) -> bool:
    if line.text.endswith((".", ",", ";", ":")):
        return False
    if is_document_title(line, median_font_size):
        return False
    if is_set_in_heading_type(line, median_font_size):
        return True
    if not line.is_upper_case:
        return False

    signals = (line.is_bold, is_larger_than_body(line, median_font_size))
    return sum(signals) >= MIN_TYPOGRAPHIC_SIGNALS


def is_document_title(line: Line, median_font_size: float) -> bool:
    if median_font_size <= 0:
        return False
    return line.max_font_size >= median_font_size * TITLE_FONT_RATIO


def is_set_in_heading_type(line: Line, median_font_size: float) -> bool:
    if median_font_size <= 0:
        return False
    return line.max_font_size >= median_font_size * HEADING_FONT_RATIO


def is_larger_than_body(line: Line, median_font_size: float) -> bool:
    if median_font_size <= 0:
        return False
    return line.max_font_size >= median_font_size * LARGE_FONT_RATIO


def build_sections(document: Document, headings: list[Heading]) -> list[DetectedSection]:
    lines = document.lines
    if not lines:
        return []

    body_headings = drop_headings_above_contact_block(headings)
    starts = section_starts(document, body_headings)
    end = lines[-1].index + 1

    sections: list[DetectedSection] = []

    contact_end = starts[0].boundary if starts else end
    contact_lines = [line for line in lines if line.index < contact_end]
    if contact_lines:
        sections.append(build_section(SectionKind.CONTACT, None, contact_lines))

    for position, start in enumerate(starts):
        next_boundary = starts[position + 1].boundary if position + 1 < len(starts) else end
        body = [line for line in lines if start.body_start <= line.index < next_boundary]
        sections.append(build_section(start.kind, start.heading, body))

    return merge_repeated_kinds(sections)


def section_starts(document: Document, headings: list[Heading]) -> list[SectionStart]:
    labelled = [
        SectionStart(
            boundary=heading.line.index,
            body_start=heading.line.index + 1,
            kind=heading.kind,
            heading=heading.line.text,
        )
        for heading in headings
    ]
    unlabelled = [
        SectionStart(boundary=index, body_start=index, kind=SectionKind.OTHER, heading=None)
        for index in reportable_column_starts(document, headings)
    ]

    return sorted(labelled + unlabelled, key=lambda start: start.boundary)


def reportable_column_starts(document: Document, headings: list[Heading]) -> list[int]:
    heading_indices = sorted(heading.line.index for heading in headings)
    taken = set(heading_indices)
    end = document.lines[-1].index + 1

    starts: list[int] = []
    for index in document.column_start_indices:
        if index in taken:
            continue
        stop = next((boundary for boundary in heading_indices if boundary > index), end)
        if words_between(document, index, stop) >= MIN_UNLABELLED_SECTION_WORDS:
            starts.append(index)

    return starts


def words_between(document: Document, start: int, stop: int) -> int:
    return sum(line.word_count for line in document.lines if start <= line.index < stop)


def drop_headings_above_contact_block(headings: list[Heading]) -> list[Heading]:
    first_recognised = next(
        (heading for heading in headings if heading.kind is not SectionKind.OTHER), None
    )
    if first_recognised is None:
        return headings

    return [heading for heading in headings if heading.line.index >= first_recognised.line.index]


def build_section(kind: SectionKind, heading: str | None, body: list[Line]) -> DetectedSection:
    first = body[0] if body else None
    last = body[-1] if body else None

    return DetectedSection(
        kind=kind,
        heading=heading,
        location=TextLocation(
            page=first.page_number if first else 1,
            line_start=first.index if first else 0,
            line_end=last.index if last else 0,
            excerpt=build_excerpt(body),
        ),
        word_count=sum(line.word_count for line in body),
    )


def build_excerpt(body: list[Line]) -> str:
    joined = " ".join(line.text for line in body).strip()
    if len(joined) <= EXCERPT_MAX_CHARS:
        return joined
    return joined[: EXCERPT_MAX_CHARS - 1].rstrip() + "…"


def merge_repeated_kinds(sections: list[DetectedSection]) -> list[DetectedSection]:
    position_of_kind: dict[SectionKind, int] = {}
    ordered: list[DetectedSection] = []

    for section in sections:
        if section.kind is SectionKind.OTHER:
            ordered.append(section)
            continue

        position = position_of_kind.get(section.kind)
        if position is None:
            position_of_kind[section.kind] = len(ordered)
            ordered.append(section)
            continue

        existing = ordered[position]
        ordered[position] = existing.model_copy(
            update={"word_count": existing.word_count + section.word_count}
        )

    return ordered
