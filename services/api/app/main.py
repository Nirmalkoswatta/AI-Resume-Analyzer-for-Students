import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AnalysisError
from app.observability import (
    REQUEST_ID_HEADER,
    bind_request_id,
    configure_logging,
    current_request_id,
    new_request_id,
)
from app.routers import analyze, health
from app.schemas.errors import ErrorResponse

logger = logging.getLogger("resume.request")

Handler = Callable[[Request], Awaitable[Response]]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Resume Analyzer API",
        version="0.1.0",
        summary="Analyzes student resumes for structure, ATS friendliness and role fit.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", REQUEST_ID_HEADER],
    )

    @app.middleware("http")
    async def trace_request(request: Request, call_next: Handler) -> Response:
        request_id = new_request_id(request.headers.get(REQUEST_ID_HEADER))
        bind_request_id(request_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request.failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers[REQUEST_ID_HEADER] = request_id

        if request.url.path != "/v1/health":
            logger.info(
                "request.completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        return response

    app.include_router(health.router, prefix="/v1")
    app.include_router(analyze.router, prefix="/v1")

    @app.exception_handler(AnalysisError)
    async def handle_analysis_error(_: Request, error: AnalysisError) -> JSONResponse:
        logger.warning(
            "analysis.rejected",
            extra={"code": error.code.value, "status": error.status_code},
        )

        body = ErrorResponse(
            code=error.code,
            message=error.message,
            remediation=error.remediation,
        )
        headers = {REQUEST_ID_HEADER: current_request_id(), **error.headers}
        return JSONResponse(
            status_code=error.status_code,
            content=body.model_dump(),
            headers=headers,
        )

    return app


app = create_app()
