from app.config import Settings
from app.pipeline.fit import assess_fit, get_role_profiles
from app.pipeline.ingest import parse_document
from app.pipeline.segment import segment
from app.pipeline.skills import count_skill_mentions, extract_skills
from app.pipeline.taxonomy import get_taxonomy
from app.schemas.analysis import Skill
from app.schemas.enums import EvidenceStrength, SectionKind, SkillSource

BACKEND_JOB = (
    "We are hiring a graduate Backend Engineer. You will build REST APIs in Python "
    "with FastAPI and PostgreSQL. Experience with Docker, CI/CD and unit testing is "
    "required. Familiarity with TypeScript, AWS and Kubernetes is a plus. Kubernetes "
    "experience is especially valued."
)


def skills_of(payload: bytes, settings: Settings) -> list[Skill]:
    document = parse_document(payload, settings)
    sections, _ = segment(document)
    return extract_skills(document, sections)


def claimed(name: str, skill_id: str) -> Skill:
    return Skill(
        name=name,
        canonical_id=skill_id,
        category="test",
        source=SkillSource.GAZETTEER,
        evidence=EvidenceStrength.CLAIMED,
        found_in=[SectionKind.SKILLS],
        confidence=0.95,
    )


def test_every_role_skill_exists_in_the_taxonomy() -> None:
    known = {entry.id for entry in get_taxonomy().entries}

    for profile in get_role_profiles():
        unknown = profile.skill_ids - known
        assert not unknown, f"{profile.name} references unknown skills: {sorted(unknown)}"


def test_predictions_are_ranked_and_bounded(single_column_pdf: bytes, settings: Settings) -> None:
    predictions = assess_fit(skills_of(single_column_pdf, settings), None).predictions

    assert predictions
    assert len(predictions) <= 3
    assert [p.confidence for p in predictions] == sorted(
        (p.confidence for p in predictions), reverse=True
    )
    assert all(0.0 < p.confidence <= 1.0 for p in predictions)


def test_backend_skills_predict_a_backend_role(
    single_column_pdf: bytes, settings: Settings
) -> None:
    predictions = assess_fit(skills_of(single_column_pdf, settings), None).predictions

    assert predictions[0].role == "Backend Developer"


def test_design_skills_predict_a_design_role() -> None:
    designer = [
        claimed("Figma", "seed:figma"),
        claimed("UI/UX design", "seed:ui-ux"),
        claimed("Wireframing", "seed:wireframing"),
        claimed("Adobe Photoshop", "seed:photoshop"),
    ]

    assert assess_fit(designer, None).predictions[0].role == "UI/UX Designer"


def test_no_skills_yields_no_predictions() -> None:
    assert assess_fit([], None).predictions == []


def test_absent_job_description_yields_no_match(
    single_column_pdf: bytes, settings: Settings
) -> None:
    skills = skills_of(single_column_pdf, settings)

    assert assess_fit(skills, None).job_description is None
    assert assess_fit(skills, "   ").job_description is None


def test_job_description_without_known_skills_yields_no_match(
    single_column_pdf: bytes, settings: Settings
) -> None:
    skills = skills_of(single_column_pdf, settings)
    vague = "We want a motivated graduate who is eager to learn and grow with us."

    assert assess_fit(skills, vague).job_description is None


def test_job_description_splits_matched_from_missing(
    single_column_pdf: bytes, settings: Settings
) -> None:
    match = assess_fit(skills_of(single_column_pdf, settings), BACKEND_JOB).job_description

    assert match is not None
    missing = {gap.skill for gap in match.missing_skills}
    assert {"Python", "REST APIs", "PostgreSQL"} <= set(match.matched_skills)
    assert {"Kubernetes", "TypeScript", "AWS"} <= missing
    assert not missing & set(match.matched_skills)
    assert 0.0 <= match.similarity <= 1.0


def test_repeated_requirements_rank_higher(single_column_pdf: bytes, settings: Settings) -> None:
    match = assess_fit(skills_of(single_column_pdf, settings), BACKEND_JOB).job_description

    assert match is not None
    assert match.missing_skills[0].skill == "Kubernetes"


def test_trailing_punctuation_does_not_hide_a_skill() -> None:
    assert "seed:postgresql" in count_skill_mentions("We use PostgreSQL.")
    assert "seed:nextjs" in count_skill_mentions("Built with Next.js.")


def test_fit_is_deterministic(single_column_pdf: bytes, settings: Settings) -> None:
    skills = skills_of(single_column_pdf, settings)

    assert (
        assess_fit(skills, BACKEND_JOB).model_dump() == assess_fit(skills, BACKEND_JOB).model_dump()
    )
