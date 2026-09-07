from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import yaml

from app.pipeline.ats import get_rubric
from app.pipeline.lexicon import HEADINGS_PATH
from app.schemas.analysis import AtsScore, Skill, Suggestion
from app.schemas.enums import EvidenceStrength, SectionKind, Severity

SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


@dataclass(frozen=True, slots=True)
class MissingSectionAdvice:
    severity: Severity
    title: str
    detail: str


@lru_cache(maxsize=1)
def get_missing_section_advice() -> dict[SectionKind, MissingSectionAdvice]:
    raw: dict[str, Any] = yaml.safe_load(HEADINGS_PATH.read_text(encoding="utf-8"))

    return {
        SectionKind(kind_name): MissingSectionAdvice(
            severity=Severity(body["severity"]),
            title=body["title"],
            detail=" ".join(body["detail"].split()),
        )
        for kind_name, body in raw.get("missing_section_advice", {}).items()
    }


MAX_NAMED_SKILLS = 3


def advise(
    ats: AtsScore, missing_sections: list[SectionKind], skills: list[Skill]
) -> list[Suggestion]:
    suggestions = [
        *suggestions_from_failed_checks(ats),
        *suggestions_from_missing_sections(missing_sections),
        *suggestions_from_unevidenced_skills(skills),
    ]
    return sorted(suggestions, key=lambda suggestion: SEVERITY_ORDER[suggestion.severity])


def suggestions_from_failed_checks(ats: AtsScore) -> list[Suggestion]:
    definitions = get_rubric().definitions

    return [
        Suggestion(
            id=f"ats.{check.id}",
            severity=check.severity,
            title=definitions[check.id].fix_title,
            detail=definitions[check.id].fix_detail,
        )
        for check in ats.checks
        if not check.passed and check.id in definitions
    ]


def suggestions_from_missing_sections(missing_sections: list[SectionKind]) -> list[Suggestion]:
    advice = get_missing_section_advice()

    return [
        Suggestion(
            id=f"section.{kind.value}",
            severity=advice[kind].severity,
            title=advice[kind].title,
            detail=advice[kind].detail,
            section=kind,
        )
        for kind in missing_sections
        if kind in advice
    ]


def suggestions_from_unevidenced_skills(skills: list[Skill]) -> list[Suggestion]:
    claimed = [skill for skill in skills if skill.evidence is EvidenceStrength.CLAIMED]
    if not claimed:
        return []

    named = ", ".join(skill.name for skill in claimed[:MAX_NAMED_SKILLS])
    remainder = len(claimed) - MAX_NAMED_SKILLS
    subject = f"{named} and {remainder} more" if remainder > 0 else named

    return [
        Suggestion(
            id="skills.unevidenced",
            severity=Severity.MEDIUM,
            title=f"Show where you used {subject}",
            detail=(
                "These appear only in your skills list. Mention each one inside an experience "
                "or project bullet so a recruiter can see the claim is backed by something."
            ),
            section=SectionKind.SKILLS,
        )
    ]
