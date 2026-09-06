from app.schemas.analysis import (
    JobDescriptionMatch,
    RoleFit,
    RolePrediction,
    Skill,
    SkillGap,
)
from app.schemas.enums import EvidenceStrength, SectionKind, SkillSource

_SKILLS = [
    Skill(
        name="Python",
        canonical_id="esco:c1a2b3",
        category="Programming languages",
        source=SkillSource.GAZETTEER,
        evidence=EvidenceStrength.DEMONSTRATED,
        found_in=[SectionKind.SKILLS, SectionKind.EXPERIENCE],
        confidence=0.98,
    ),
    Skill(
        name="React",
        canonical_id="esco:d4e5f6",
        category="Web frameworks",
        source=SkillSource.GAZETTEER,
        evidence=EvidenceStrength.DEMONSTRATED,
        found_in=[SectionKind.SKILLS, SectionKind.EXPERIENCE],
        confidence=0.95,
    ),
    Skill(
        name="PostgreSQL",
        canonical_id="esco:a7b8c9",
        category="Databases",
        source=SkillSource.GAZETTEER,
        evidence=EvidenceStrength.CLAIMED,
        found_in=[SectionKind.SKILLS],
        confidence=0.91,
    ),
    Skill(
        name="Docker",
        canonical_id=None,
        category="Tooling",
        source=SkillSource.NER,
        evidence=EvidenceStrength.CLAIMED,
        found_in=[SectionKind.SKILLS],
        confidence=0.64,
    ),
]

_ROLE_PREDICTIONS = [
    RolePrediction(role="Software Engineer", confidence=0.71),
    RolePrediction(role="Web Developer", confidence=0.18),
    RolePrediction(role="Data Analyst", confidence=0.06),
]

_JOB_MATCH = JobDescriptionMatch(
    similarity=0.62,
    matched_skills=["Python", "React", "Git", "REST APIs"],
    missing_skills=[
        SkillGap(skill="TypeScript", importance=0.88),
        SkillGap(skill="CI/CD", importance=0.74),
        SkillGap(skill="Unit testing", importance=0.69),
        SkillGap(skill="AWS", importance=0.55),
    ],
)


def fixture_skills() -> list[Skill]:
    return list(_SKILLS)


def fixture_role_fit(job_description: str | None) -> RoleFit:
    return RoleFit(
        predictions=list(_ROLE_PREDICTIONS),
        job_description=_JOB_MATCH if job_description else None,
    )
