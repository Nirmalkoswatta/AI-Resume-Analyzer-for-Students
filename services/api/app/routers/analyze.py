from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config import Settings, get_settings
from app.fixtures import build_fixture_result
from app.schemas.analysis import AnalysisResult
from app.schemas.errors import ErrorResponse
from app.upload import read_validated_upload

router = APIRouter(tags=["analysis"])

MAX_JOB_DESCRIPTION_CHARS = 20_000

ANALYZE_RESPONSES: dict[int | str, dict[str, object]] = {
    413: {"model": ErrorResponse, "description": "Upload exceeds the size limit."},
    415: {"model": ErrorResponse, "description": "Upload is not a PDF."},
    422: {"model": ErrorResponse, "description": "PDF could not be analyzed."},
    429: {"model": ErrorResponse, "description": "Too many requests."},
}


@router.post("/analyze", response_model=AnalysisResult, responses=ANALYZE_RESPONSES)
async def analyze(
    settings: Annotated[Settings, Depends(get_settings)],
    resume: Annotated[UploadFile, File(description="Resume as a PDF, 5 MB maximum.")],
    job_description: Annotated[
        str | None,
        Form(
            max_length=MAX_JOB_DESCRIPTION_CHARS,
            description="Optional target job posting to produce a gap analysis against.",
        ),
    ] = None,
) -> AnalysisResult:
    await read_validated_upload(resume, settings)
    return build_fixture_result(job_description)
