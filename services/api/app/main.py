from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AnalysisError
from app.routers import analyze, health
from app.schemas.errors import ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()

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
        allow_headers=["Content-Type"],
    )

    app.include_router(health.router, prefix="/v1")
    app.include_router(analyze.router, prefix="/v1")

    @app.exception_handler(AnalysisError)
    async def handle_analysis_error(_: Request, error: AnalysisError) -> JSONResponse:
        body = ErrorResponse(
            code=error.code,
            message=error.message,
            remediation=error.remediation,
        )
        return JSONResponse(status_code=error.status_code, content=body.model_dump())

    return app


app = create_app()
