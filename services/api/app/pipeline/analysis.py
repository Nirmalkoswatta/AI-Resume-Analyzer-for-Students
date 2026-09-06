from datetime import UTC, datetime
from uuid import uuid4

from app.config import MODEL_VERSION, RUBRIC_VERSION, Settings
from app.fixtures import fixture_role_fit, fixture_skills
from app.pipeline.advise import advise
from app.pipeline.ats import evaluate
from app.pipeline.document import Document
from app.pipeline.ingest import parse_document
from app.pipeline.segment import segment
from app.schemas.analysis import AnalysisResult, DocumentStats


def analyze_resume(
    payload: bytes, job_description: str | None, settings: Settings
) -> AnalysisResult:
    document = parse_document(payload, settings)
    sections, missing_sections = segment(document)
    ats = evaluate(document, sections)

    return AnalysisResult(
        analysis_id=str(uuid4()),
        created_at=datetime.now(UTC),
        rubric_version=RUBRIC_VERSION,
        model_version=MODEL_VERSION,
        document=describe_document(document),
        sections=sections,
        missing_sections=missing_sections,
        skills=fixture_skills(),
        ats=ats,
        fit=fixture_role_fit(job_description),
        suggestions=advise(ats, missing_sections),
    )


def describe_document(document: Document) -> DocumentStats:
    return DocumentStats(
        page_count=document.page_count,
        word_count=document.word_count,
        column_count=document.column_count,
        machine_readable=document.character_count > 0,
        has_tables=document.table_count > 0,
        has_images=document.image_count > 0,
        text_in_header_footer=document.has_text_in_header_footer,
        font_families=list(document.font_families),
    )
