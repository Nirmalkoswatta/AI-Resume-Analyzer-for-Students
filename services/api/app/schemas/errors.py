from pydantic import BaseModel, Field

from app.schemas.enums import AnalysisErrorCode


class ErrorResponse(BaseModel):
    code: AnalysisErrorCode = Field(description="Stable machine-readable failure identifier.")
    message: str = Field(description="Human-readable explanation safe to display to the student.")
    remediation: str | None = Field(
        default=None,
        description="Concrete action the student can take to resolve the failure.",
    )
