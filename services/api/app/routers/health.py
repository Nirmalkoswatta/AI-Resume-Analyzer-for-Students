from fastapi import APIRouter
from pydantic import BaseModel

from app.config import MODEL_VERSION, RUBRIC_VERSION
from app.schemas.analysis import SCHEMA_VERSION

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    schema_version: str
    rubric_version: str
    model_version: str
    models_loaded: bool


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        schema_version=SCHEMA_VERSION,
        rubric_version=RUBRIC_VERSION,
        model_version=MODEL_VERSION,
        models_loaded=True,
    )
