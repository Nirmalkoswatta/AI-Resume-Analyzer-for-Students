from app.config import Settings
from app.pipeline.advise import advise
from app.pipeline.ats import evaluate
from app.pipeline.ingest import parse_document
from app.pipeline.segment import segment
from app.pipeline.skills import extract_skills
from app.pipeline.taxonomy import get_taxonomy, normalise_surface
from app.schemas.analysis import Skill
from app.schemas.enums import EvidenceStrength, SectionKind, SkillSource


def skills_for(payload: bytes, settings: Settings) -> list[Skill]:
    document = parse_document(payload, settings)
    sections, _ = segment(document)
    return extract_skills(document, sections)


def names(skills: list[Skill]) -> set[str]:
    return {skill.name for skill in skills}


def test_taxonomy_ids_and_surfaces_are_unique() -> None:
    taxonomy = get_taxonomy()
    ids = [entry.id for entry in taxonomy.entries]

    assert len(ids) == len(set(ids))
    assert all(entry.surfaces for entry in taxonomy.entries)
    assert all(entry.category for entry in taxonomy.entries)


def test_aliases_resolve_to_canonical_names() -> None:
    taxonomy = get_taxonomy()

    assert taxonomy.by_surface["js"].name == "JavaScript"
    assert taxonomy.by_surface["postgres"].name == "PostgreSQL"
    assert taxonomy.by_surface["k8s"].name == "Kubernetes"
    assert taxonomy.by_surface[normalise_surface("Node JS")].name == "Node.js"


def test_extracts_skills_from_the_document(single_column_pdf: bytes, settings: Settings) -> None:
    found = names(skills_for(single_column_pdf, settings))

    assert {"Python", "React", "PostgreSQL", "SQL", "Git"} <= found


def test_skills_used_in_experience_are_demonstrated(
    single_column_pdf: bytes, settings: Settings
) -> None:
    python = next(s for s in skills_for(single_column_pdf, settings) if s.name == "Python")

    assert python.evidence is EvidenceStrength.DEMONSTRATED
    assert SectionKind.EXPERIENCE in python.found_in


def test_skills_only_listed_are_claimed(single_column_pdf: bytes, settings: Settings) -> None:
    git = next(s for s in skills_for(single_column_pdf, settings) if s.name == "Git")

    assert git.evidence is EvidenceStrength.CLAIMED
    assert git.found_in == [SectionKind.SKILLS]


def test_multi_word_skills_beat_their_parts(single_column_pdf: bytes, settings: Settings) -> None:
    found = names(skills_for(single_column_pdf, settings))

    assert "REST APIs" in found


def test_ambiguous_short_names_match_only_in_skills_section(
    ambiguous_skills_pdf: bytes, settings: Settings
) -> None:
    found = names(skills_for(ambiguous_skills_pdf, settings))

    assert {"C", "R", "Go", "Python"} <= found


def test_prose_does_not_trigger_short_name_matches(
    ambiguous_skills_pdf: bytes, settings: Settings
) -> None:
    go = next(skill for skill in skills_for(ambiguous_skills_pdf, settings) if skill.name == "Go")

    assert go.found_in == [SectionKind.SKILLS]


def test_typos_are_recovered_with_lower_confidence(
    misspelled_skills_pdf: bytes, settings: Settings
) -> None:
    extracted = skills_for(misspelled_skills_pdf, settings)
    kubernetes = next(skill for skill in extracted if skill.name == "Kubernetes")

    assert kubernetes.confidence < 0.95
    assert "JavaScript" in names(extracted)


def test_every_skill_carries_provenance(single_column_pdf: bytes, settings: Settings) -> None:
    for skill in skills_for(single_column_pdf, settings):
        assert skill.canonical_id
        assert skill.category
        assert skill.found_in
        assert skill.source is SkillSource.GAZETTEER
        assert 0.0 < skill.confidence <= 1.0


def test_demonstrated_skills_are_listed_first(single_column_pdf: bytes, settings: Settings) -> None:
    evidences = [skill.evidence for skill in skills_for(single_column_pdf, settings)]
    demonstrated_positions = [
        index
        for index, evidence in enumerate(evidences)
        if evidence is EvidenceStrength.DEMONSTRATED
    ]
    claimed_positions = [
        index for index, evidence in enumerate(evidences) if evidence is EvidenceStrength.CLAIMED
    ]

    assert (
        not demonstrated_positions
        or not claimed_positions
        or (max(demonstrated_positions) < min(claimed_positions))
    )


def test_extraction_is_deterministic(single_column_pdf: bytes, settings: Settings) -> None:
    first = skills_for(single_column_pdf, settings)
    second = skills_for(single_column_pdf, settings)

    assert [skill.model_dump() for skill in first] == [skill.model_dump() for skill in second]


def test_unevidenced_skills_produce_a_suggestion(
    single_column_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(single_column_pdf, settings)
    sections, missing = segment(document)
    extracted = extract_skills(document, sections)
    suggestions = advise(evaluate(document, sections), missing, extracted)

    assert any(suggestion.id == "skills.unevidenced" for suggestion in suggestions)


def test_no_unevidenced_suggestion_when_all_demonstrated(
    single_column_pdf: bytes, settings: Settings
) -> None:
    document = parse_document(single_column_pdf, settings)
    sections, _ = segment(document)
    demonstrated = [
        Skill(
            name="Python",
            canonical_id="seed:python",
            category="Programming languages",
            source=SkillSource.GAZETTEER,
            evidence=EvidenceStrength.DEMONSTRATED,
            found_in=[SectionKind.EXPERIENCE],
            confidence=0.95,
        )
    ]
    suggestions = advise(evaluate(document, sections), [], demonstrated)

    assert all(suggestion.id != "skills.unevidenced" for suggestion in suggestions)
