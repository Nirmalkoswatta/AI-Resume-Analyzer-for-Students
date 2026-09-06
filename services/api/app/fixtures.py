from datetime import UTC, datetime
from uuid import uuid4

from app.config import MODEL_VERSION, RUBRIC_VERSION
from app.schemas.analysis import (
    AnalysisResult,
    AtsCheck,
    AtsScore,
    DetectedSection,
    DocumentStats,
    JobDescriptionMatch,
    RoleFit,
    RolePrediction,
    Skill,
    SkillGap,
    Suggestion,
    TextLocation,
)
from app.schemas.enums import EvidenceStrength, SectionKind, Severity, SkillSource

_DOCUMENT = DocumentStats(
    page_count=1,
    word_count=412,
    column_count=2,
    machine_readable=True,
    has_tables=True,
    has_images=False,
    text_in_header_footer=True,
    font_families=["Calibri", "Cambria Math"],
)

_SECTIONS = [
    DetectedSection(
        kind=SectionKind.CONTACT,
        heading=None,
        location=TextLocation(page=1, line_start=0, line_end=3, excerpt="Priya Fernando"),
        word_count=12,
    ),
    DetectedSection(
        kind=SectionKind.EDUCATION,
        heading="EDUCATION",
        location=TextLocation(
            page=1,
            line_start=4,
            line_end=9,
            excerpt="BSc Computer Science, University of Colombo",
        ),
        word_count=48,
    ),
    DetectedSection(
        kind=SectionKind.EXPERIENCE,
        heading="Work History",
        location=TextLocation(
            page=1,
            line_start=10,
            line_end=24,
            excerpt="Software Engineering Intern, Reddy Labs",
        ),
        word_count=186,
    ),
    DetectedSection(
        kind=SectionKind.SKILLS,
        heading="SKILLS",
        location=TextLocation(
            page=1,
            line_start=25,
            line_end=31,
            excerpt="Python, JavaScript, React, SQL, Git, Docker",
        ),
        word_count=34,
    ),
]

_MISSING_SECTIONS = [SectionKind.PROJECTS, SectionKind.SUMMARY]

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

_ATS_CHECKS = [
    AtsCheck(
        id="single_column_layout",
        label="Single-column layout",
        passed=False,
        weight=0.20,
        severity=Severity.CRITICAL,
        explanation=(
            "Two text columns were detected. Most applicant tracking systems read a page "
            "left to right and will interleave the two columns into unreadable text."
        ),
    ),
    AtsCheck(
        id="no_layout_tables",
        label="No tables used for layout",
        passed=False,
        weight=0.15,
        severity=Severity.HIGH,
        explanation="Content sits inside a table, which many parsers flatten or skip entirely.",
    ),
    AtsCheck(
        id="text_outside_header_footer",
        label="No content in headers or footers",
        passed=False,
        weight=0.10,
        severity=Severity.HIGH,
        explanation="Your email address is in the page header, where most parsers never look.",
    ),
    AtsCheck(
        id="standard_section_headings",
        label="Recognisable section headings",
        passed=True,
        weight=0.15,
        severity=Severity.MEDIUM,
        explanation="Headings map cleanly onto the sections parsers expect to find.",
    ),
    AtsCheck(
        id="machine_readable_text",
        label="Selectable text layer",
        passed=True,
        weight=0.20,
        severity=Severity.CRITICAL,
        explanation="The document contains real text rather than a scanned image.",
    ),
    AtsCheck(
        id="contact_block_parseable",
        label="Contact details detected",
        passed=True,
        weight=0.10,
        severity=Severity.HIGH,
        explanation="An email address and phone number were found near the top of page one.",
    ),
    AtsCheck(
        id="consistent_date_formats",
        label="Consistent date formats",
        passed=True,
        weight=0.05,
        severity=Severity.LOW,
        explanation="All roles use the same month and year format.",
    ),
    AtsCheck(
        id="appropriate_length",
        label="Appropriate length",
        passed=True,
        weight=0.05,
        severity=Severity.LOW,
        explanation="One page is the right length for a student resume.",
    ),
]

_SUGGESTIONS = [
    Suggestion(
        id="collapse_columns",
        severity=Severity.CRITICAL,
        title="Switch to a single-column layout",
        detail=(
            "Your skills sidebar sits in a second column. Move it into the main flow so a "
            "parser reads your resume in the order a human does."
        ),
        section=None,
        location=None,
    ),
    Suggestion(
        id="move_contact_out_of_header",
        severity=Severity.HIGH,
        title="Move your email out of the page header",
        detail=(
            "Contact details in a header are invisible to most parsers. Put your name, email "
            "and phone number in the body of the page instead."
        ),
        section=SectionKind.CONTACT,
        location=TextLocation(page=1, line_start=0, line_end=0, excerpt="priya.f@example.com"),
    ),
    Suggestion(
        id="quantify_bullets",
        severity=Severity.HIGH,
        title="Add measurable outcomes to 3 bullet points",
        detail=(
            "Three bullets describe responsibilities without results. Rewrite "
            "Worked on the reporting dashboard as Cut report load time from 8s to 1.2s "
            "for 400 weekly users."
        ),
        section=SectionKind.EXPERIENCE,
        location=TextLocation(
            page=1,
            line_start=14,
            line_end=14,
            excerpt="Worked on the reporting dashboard",
        ),
    ),
    Suggestion(
        id="add_projects_section",
        severity=Severity.MEDIUM,
        title="Add a Projects section",
        detail=(
            "With one internship so far, coursework and personal projects are the strongest "
            "evidence you can show. Two projects with links would fill the gap."
        ),
        section=SectionKind.PROJECTS,
        location=None,
    ),
    Suggestion(
        id="evidence_claimed_skills",
        severity=Severity.MEDIUM,
        title="Back up PostgreSQL and Docker with evidence",
        detail=(
            "Both appear only in your skills list. Mention where you used them in an "
            "experience or project bullet so the claim is verifiable."
        ),
        section=SectionKind.SKILLS,
        location=None,
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


def build_fixture_result(job_description: str | None = None) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=str(uuid4()),
        created_at=datetime.now(UTC),
        rubric_version=RUBRIC_VERSION,
        model_version=MODEL_VERSION,
        document=_DOCUMENT,
        sections=_SECTIONS,
        missing_sections=_MISSING_SECTIONS,
        skills=_SKILLS,
        ats=AtsScore(score=55.0, rubric_version=RUBRIC_VERSION, checks=_ATS_CHECKS),
        fit=RoleFit(
            predictions=_ROLE_PREDICTIONS,
            job_description=_JOB_MATCH if job_description else None,
        ),
        suggestions=_SUGGESTIONS,
    )
