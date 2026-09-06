from app.config import Settings
from app.pipeline.ingest import parse_document
from app.pipeline.lexicon import get_heading_lexicon, normalise
from app.pipeline.segment import segment
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
