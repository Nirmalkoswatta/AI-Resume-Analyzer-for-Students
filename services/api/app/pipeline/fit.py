from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.pipeline.skills import count_skill_mentions
from app.pipeline.taxonomy import get_taxonomy
from app.schemas.analysis import (
    JobDescriptionMatch,
    RoleFit,
    RolePrediction,
    Skill,
    SkillGap,
)
from app.schemas.enums import EvidenceStrength

ROLES_PATH = Path(__file__).resolve().parents[1] / "resources" / "roles.yaml"

TOP_ROLE_COUNT = 3
MAX_REPORTED_GAPS = 8
DEMONSTRATED_WEIGHT = 1.0
CLAIMED_WEIGHT = 0.6


@dataclass(frozen=True, slots=True)
class RoleProfile:
    name: str
    skill_ids: frozenset[str]


@lru_cache(maxsize=1)
def get_role_profiles() -> tuple[RoleProfile, ...]:
    raw: dict[str, Any] = yaml.safe_load(ROLES_PATH.read_text(encoding="utf-8"))

    return tuple(
        RoleProfile(name=role["name"], skill_ids=frozenset(role["skills"])) for role in raw["roles"]
    )


def assess_fit(skills: list[Skill], job_description: str | None) -> RoleFit:
    return RoleFit(
        predictions=predict_roles(skills),
        job_description=match_job_description(skills, job_description),
    )


@lru_cache(maxsize=1)
def get_skill_distinctiveness() -> dict[str, float]:
    profiles = get_role_profiles()
    appearances = Counter(skill_id for profile in profiles for skill_id in profile.skill_ids)
    return {skill_id: 1.0 / count for skill_id, count in appearances.items()}


def predict_roles(skills: list[Skill]) -> list[RolePrediction]:
    weights = {skill.canonical_id: weight_for(skill) for skill in skills if skill.canonical_id}
    if not weights:
        return []

    distinctiveness = get_skill_distinctiveness()
    scored = [
        (profile.name, coverage(profile, weights, distinctiveness))
        for profile in get_role_profiles()
    ]
    total = sum(score for _, score in scored)
    if total <= 0:
        return []

    ranked = sorted(scored, key=lambda item: (-item[1], item[0]))[:TOP_ROLE_COUNT]

    return [
        RolePrediction(role=name, confidence=round(score / total, 2))
        for name, score in ranked
        if score > 0
    ]


def weight_for(skill: Skill) -> float:
    return (
        DEMONSTRATED_WEIGHT if skill.evidence is EvidenceStrength.DEMONSTRATED else CLAIMED_WEIGHT
    )


def coverage(
    profile: RoleProfile, weights: dict[str, float], distinctiveness: dict[str, float]
) -> float:
    available = sum(distinctiveness[skill_id] for skill_id in profile.skill_ids)
    if available <= 0:
        return 0.0

    matched = sum(
        weights.get(skill_id, 0.0) * distinctiveness[skill_id] for skill_id in profile.skill_ids
    )
    return matched / available


def match_job_description(
    skills: list[Skill], job_description: str | None
) -> JobDescriptionMatch | None:
    if not job_description or not job_description.strip():
        return None

    required = count_skill_mentions(job_description)
    if not required:
        return None

    taxonomy_names = {entry.id: entry.name for entry in get_taxonomy().entries}
    owned = {skill.canonical_id for skill in skills if skill.canonical_id}

    matched = [taxonomy_names[skill_id] for skill_id in required if skill_id in owned]
    missing_ids = [skill_id for skill_id in required if skill_id not in owned]
    highest = max(required.values())

    gaps = sorted(
        (
            SkillGap(
                skill=taxonomy_names[skill_id],
                importance=round(required[skill_id] / highest, 2),
            )
            for skill_id in missing_ids
        ),
        key=lambda gap: (-gap.importance, gap.skill),
    )

    return JobDescriptionMatch(
        similarity=round(len(matched) / len(required), 2),
        matched_skills=sorted(matched),
        missing_skills=gaps[:MAX_REPORTED_GAPS],
    )
