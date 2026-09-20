from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.pipeline.document import Document
from app.schemas.analysis import AtsCheck, AtsScore, DetectedSection
from app.schemas.enums import SectionKind, Severity

RUBRIC_PATH = Path(__file__).resolve().parents[1] / "resources" / "ats_rubric.yaml"

MAX_RESUME_PAGES = 1


@dataclass(frozen=True, slots=True)
class CheckDefinition:
    id: str
    label: str
    weight: float
    severity: Severity
    passed_explanation: str
    failed_explanation: str
    fix_title: str
    fix_detail: str


@dataclass(frozen=True)
class Rubric:
    version: str
    definitions: dict[str, CheckDefinition]


def collapse(text: str) -> str:
    return " ".join(text.split())


@lru_cache(maxsize=1)
def get_rubric() -> Rubric:
    raw: dict[str, Any] = yaml.safe_load(RUBRIC_PATH.read_text(encoding="utf-8"))

    definitions = {
        check_id: CheckDefinition(
            id=check_id,
            label=body["label"],
            weight=float(body["weight"]),
            severity=Severity(body["severity"]),
            passed_explanation=collapse(body["passed"]),
            failed_explanation=collapse(body["failed"]),
            fix_title=collapse(body["fix_title"]),
            fix_detail=collapse(body["fix_detail"]),
        )
        for check_id, body in raw["checks"].items()
    }

    return Rubric(version=str(raw["version"]), definitions=definitions)


def evaluate(document: Document, sections: list[DetectedSection]) -> AtsScore:
    rubric = get_rubric()
    outcomes = {
        "machine_readable_text": document.character_count > 0,
        "single_column_layout": document.column_count == 1,
        "no_layout_tables": document.table_count == 0,
        "text_outside_header_footer": not document.has_text_in_header_footer,
        "recognisable_section_headings": has_recognisable_headings(sections),
        "appropriate_length": document.page_count <= MAX_RESUME_PAGES,
    }

    checks = [
        build_check(rubric.definitions[check_id], passed) for check_id, passed in outcomes.items()
    ]
    earned = sum(check.weight for check in checks if check.passed)
    available = sum(check.weight for check in checks)
    score = (earned / available * 100.0) if available > 0 else 0.0

    return AtsScore(score=round(score, 1), rubric_version=rubric.version, checks=checks)


def build_check(definition: CheckDefinition, passed: bool) -> AtsCheck:
    return AtsCheck(
        id=definition.id,
        label=definition.label,
        passed=passed,
        weight=definition.weight,
        severity=definition.severity,
        explanation=definition.passed_explanation if passed else definition.failed_explanation,
    )


def has_recognisable_headings(sections: list[DetectedSection]) -> bool:
    labelled = [section for section in sections if section.heading is not None]
    if not labelled:
        return False
    return all(section.kind is not SectionKind.OTHER for section in labelled)
