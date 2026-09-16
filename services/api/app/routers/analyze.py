import logging
import time
from functools import lru_cache
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.config import Settings, get_settings
from app.errors import RateLimitedError
from app.observability import describe_analysis
from app.pipeline.analysis import analyze_resume
from app.ratelimit import SlidingWindowLimiter, build_limiter, client_key, monotonic_now
from app.schemas.analysis import AnalysisResult
from app.schemas.errors import ErrorResponse
from app.upload import read_validated_upload

router = APIRouter(tags=["analysis"])
logger = logging.getLogger("resume.analysis")


@lru_cache(maxsize=1)
def get_limiter() -> SlidingWindowLimiter:
    return build_limiter(get_settings())


def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    if settings.rate_limit_requests <= 0:
        return

    key = client_key(request, settings.trusted_proxy_count)
    retry_after = get_limiter().check(key, monotonic_now())
    if retry_after is not None:
        raise RateLimitedError(ceil(retry_after))


MAX_JOB_DESCRIPTION_CHARS = 20_000

ANALYZE_RESPONSES: dict[int | str, dict[str, object]] = {
    413: {"model": ErrorResponse, "description": "Upload exceeds the size limit."},
    415: {"model": ErrorResponse, "description": "Upload is not a PDF."},
    422: {"model": ErrorResponse, "description": "PDF could not be analyzed."},
    429: {"model": ErrorResponse, "description": "Too many requests."},
}


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    responses=ANALYZE_RESPONSES,
    dependencies=[Depends(enforce_rate_limit)],
)
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
    payload = await read_validated_upload(resume, settings)

    started = time.perf_counter()
    result = analyze_resume(payload, job_description, settings)
    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    logger.info(
        "analysis.completed",
        extra={
            "upload_bytes": len(payload),
            "with_job_description": job_description is not None,
            "duration_ms": duration_ms,
            **describe_analysis(result),
        },
    )

    return result
