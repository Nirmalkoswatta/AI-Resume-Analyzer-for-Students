from app.config import Settings
from app.pipeline.document import Line, Span
from app.pipeline.ingest import parse_document
from app.pipeline.lexicon import get_heading_lexicon, normalise
from app.pipeline.segment import looks_like_heading, segment
from app.schemas.analysis import DetectedSection
from app.schemas.enums import SectionKind


def kinds_of(payload: bytes, settings: Settings) -> list[SectionKind]:
    document = parse_document(payload, settings)
    sections, _ = segment(document)
    return [section.kind for section in sections]


def test_finds_standard_sections(single_column_pdf: bytes, settings: Settings) -> None:
    assert kinds_of(single_column_pdf, settings) == [
        SectionKind.CONTACT,
        SectionKind.EDUCATION,
        SectionKind.EXPERIENCE,
        SectionKind.PROJECTS,
        SectionKind.SKILLS,
    ]


def test_synonym_headings_map_to_canonical_kinds(sample_resume: bytes, settings: Settings) -> None:
    document = parse_document(sample_resume, settings)
    sections, _ = segment(document)
    experience = next(s for s in sections if s.kind is SectionKind.EXPERIENCE)

    assert experience.heading == "WORK HISTORY"


def test_content_above_first_heading_becomes_contact(
    sample_resume: bytes, settings: Settings
) -> None:
    document = parse_document(sample_resume, settings)
    sections, _ = segment(document)
    contact = sections[0]

    assert contact.kind is SectionKind.CONTACT
    assert contact.heading is None
    assert "Priya Fernando" in contact.location.excerpt


def test_unrecognised_headings_are_flagged_as_other(
    creative_headings_pdf: bytes, settings: Settings
) -> None:
    kinds = kinds_of(creative_headings_pdf, settings)

    assert SectionKind.OTHER in kinds
    assert SectionKind.EXPERIENCE not in kinds


def test_missing_sections_are_reported(sample_resume: bytes, settings: Settings) -> None:
    document = parse_document(sample_resume, settings)
    _, missing = segment(document)

    assert SectionKind.PROJECTS in missing
    assert SectionKind.EDUCATION not in missing


def test_sections_carry_word_counts_and_location(
    single_column_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(single_column_pdf, settings)
    sections, _ = segment(document)
    skills = next(s for s in sections if s.kind is SectionKind.SKILLS)

    assert skills.word_count > 0
    assert skills.location.page == 1
    assert skills.location.line_end >= skills.location.line_start


def test_excerpt_respects_schema_limit(single_column_pdf: bytes, settings: Settings) -> None:
    document = parse_document(single_column_pdf, settings)
    sections, _ = segment(document)

    assert all(len(section.location.excerpt) <= 400 for section in sections)


def test_lexicon_normalisation_is_punctuation_insensitive() -> None:
    lexicon = get_heading_lexicon()

    assert normalise("  Work   History:  ") == "work history"
    assert lexicon.kind_for("WORK HISTORY") is SectionKind.EXPERIENCE
    assert lexicon.kind_for("Technical Skills") is SectionKind.SKILLS
    assert lexicon.kind_for("Nonsense Heading") is None


def test_repeated_headings_across_pages_are_merged(two_page_pdf: bytes, settings: Settings) -> None:
    kinds = kinds_of(two_page_pdf, settings)

    assert len(kinds) == len(set(kinds))
    assert SectionKind.EDUCATION in kinds


def test_merged_section_keeps_the_combined_word_count(
    two_page_pdf: bytes, single_column_pdf: bytes, settings: Settings
) -> None:
    def skills_words(payload: bytes) -> int:
        document = parse_document(payload, settings)
        sections, _ = segment(document)
        return next(s for s in sections if s.kind is SectionKind.SKILLS).word_count

    assert skills_words(two_page_pdf) > skills_words(single_column_pdf)


def test_sections_follow_visual_order_when_blocks_are_scrambled(
    scrambled_order_pdf: bytes, settings: Settings
) -> None:
    assert kinds_of(scrambled_order_pdf, settings) == [
        SectionKind.CONTACT,
        SectionKind.EXPERIENCE,
        SectionKind.EDUCATION,
        SectionKind.SKILLS,
    ]


def test_a_heading_never_loses_its_body_to_block_order(
    scrambled_order_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(scrambled_order_pdf, settings)
    sections, _ = segment(document)

    assert all(section.word_count > 0 for section in sections)


def test_title_case_headings_are_recognised(
    title_case_headings_pdf: bytes, settings: Settings
) -> None:
    assert kinds_of(title_case_headings_pdf, settings) == [
        SectionKind.CONTACT,
        SectionKind.SUMMARY,
        SectionKind.SKILLS,
        SectionKind.EXPERIENCE,
        SectionKind.EDUCATION,
        SectionKind.LANGUAGES,
    ]


def test_a_skills_section_titled_skill_highlights_is_not_reported_missing(
    title_case_headings_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(title_case_headings_pdf, settings)
    _, missing = segment(document)

    assert SectionKind.SKILLS not in missing


def heading_line(text: str, size: float) -> Line:
    return Line(
        index=0,
        page_number=1,
        spans=(
            Span(
                text=text,
                font="helv",
                size=size,
                bold=False,
                italic=False,
                x0=0.0,
                top=0.0,
                x1=1.0,
                bottom=1.0,
            ),
        ),
        x0=0.0,
        top=0.0,
        x1=100.0,
        bottom=10.0,
    )


def test_a_title_case_heading_outside_the_lexicon_is_still_a_heading() -> None:
    assert looks_like_heading(heading_line("Things I Have Shipped", 13.0), 10.0)


def test_body_text_at_body_size_is_not_a_heading() -> None:
    assert not looks_like_heading(heading_line("Built REST endpoints in Python", 10.0), 10.0)


def test_the_document_title_is_not_treated_as_a_heading() -> None:
    assert not looks_like_heading(heading_line("Priya Fernando", 24.0), 10.0)


def sections_of(payload: bytes, settings: Settings) -> list[DetectedSection]:
    document = parse_document(payload, settings)
    sections, _ = segment(document)
    return sections


def test_a_sidebar_section_does_not_absorb_the_next_column(
    unlabelled_main_column_pdf: bytes, settings: Settings
) -> None:
    languages = next(
        section
        for section in sections_of(unlabelled_main_column_pdf, settings)
        if section.kind is SectionKind.LANGUAGES
    )

    assert languages.word_count == 2


def test_an_unlabelled_column_opening_becomes_its_own_section(
    unlabelled_main_column_pdf: bytes, settings: Settings
) -> None:
    unlabelled = [
        section
        for section in sections_of(unlabelled_main_column_pdf, settings)
        if section.kind is SectionKind.OTHER and section.heading is None
    ]

    assert len(unlabelled) == 1
    assert unlabelled[0].word_count == 17


def test_a_stray_line_is_too_small_to_report_as_a_section(
    stray_line_main_column_pdf: bytes, settings: Settings
) -> None:
    sections = sections_of(stray_line_main_column_pdf, settings)

    assert not [
        section
        for section in sections
        if section.kind is SectionKind.OTHER and section.heading is None
    ]
