from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    EvidenceStrength,
    SectionKind,
    Severity,
    SkillSource,
)

SCHEMA_VERSION = "1.0.0"


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TextLocation(Frozen):
    page: int = Field(ge=1, description="One-based page number.")
    line_start: int = Field(ge=0)
    line_end: int = Field(ge=0)
    excerpt: str = Field(max_length=400)


class DocumentStats(Frozen):
    page_count: int = Field(ge=1)
    word_count: int = Field(ge=0)
    column_count: int = Field(ge=1, description="Detected text columns on the densest page.")
    machine_readable: bool = Field(
        description="False when the resume is a scanned image with no extractable text layer."
    )
    has_tables: bool
    has_images: bool
    text_in_header_footer: bool
    font_families: list[str]


class DetectedSection(Frozen):
    kind: SectionKind
    heading: str | None = Field(default=None, description="Verbatim heading text as written.")
    location: TextLocation
    word_count: int = Field(ge=0)


class Skill(Frozen):
    name: str
    canonical_id: str | None = Field(
        default=None, description="Identifier in the ESCO or O*NET taxonomy when matched."
    )
    category: str | None = None
    source: SkillSource
    evidence: EvidenceStrength = Field(
        description="Demonstrated when the skill appears inside experience or project prose."
    )
    found_in: list[SectionKind]
    confidence: float = Field(ge=0.0, le=1.0)


class AtsCheck(Frozen):
    id: str
    label: str
    passed: bool
    weight: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str


class AtsScore(Frozen):
    score: float = Field(ge=0.0, le=100.0)
    rubric_version: str
    checks: list[AtsCheck]


class RolePrediction(Frozen):
    role: str
    confidence: float = Field(ge=0.0, le=1.0)


class SkillGap(Frozen):
    skill: str
    importance: float = Field(ge=0.0, le=1.0)


class JobDescriptionMatch(Frozen):
    similarity: float = Field(ge=0.0, le=1.0)
    matched_skills: list[str]
    missing_skills: list[SkillGap]


class RoleFit(Frozen):
    predictions: list[RolePrediction]
    job_description: JobDescriptionMatch | None = None


class Suggestion(Frozen):
    id: str
    severity: Severity
    title: str
    detail: str
    section: SectionKind | None = None
    location: TextLocation | None = None


class AnalysisResult(Frozen):
    analysis_id: str
    created_at: datetime
    schema_version: str = SCHEMA_VERSION
    rubric_version: str
    model_version: str
    document: DocumentStats
    sections: list[DetectedSection]
    missing_sections: list[SectionKind]
    skills: list[Skill]
    ats: AtsScore
    fit: RoleFit
    suggestions: list[Suggestion]
