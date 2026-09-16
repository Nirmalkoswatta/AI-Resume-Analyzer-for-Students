import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from app.schemas.analysis import AnalysisResult

REQUEST_ID_HEADER = "X-Request-Id"
MAX_REQUEST_ID_LENGTH = 64

_request_id: ContextVar[str] = ContextVar("request_id", default="")

_RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }

        request_id = _request_id.get()
        if request_id:
            payload["request_id"] = request_id

        payload.update(
            {key: value for key, value in record.__dict__.items() if key not in _RESERVED}
        )

        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["traceback"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def new_request_id(supplied: str | None) -> str:
    if supplied:
        cleaned = "".join(
            character for character in supplied if character.isalnum() or character in "-_"
        )
        if cleaned:
            return cleaned[:MAX_REQUEST_ID_LENGTH]
    return uuid.uuid4().hex


def bind_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def current_request_id() -> str:
    return _request_id.get()


def describe_analysis(result: AnalysisResult) -> dict[str, Any]:
    document = result.document

    return {
        "pages": document.page_count,
        "words": document.word_count,
        "columns": document.column_count,
        "has_tables": document.has_tables,
        "has_images": document.has_images,
        "running_furniture": document.text_in_header_footer,
        "font_count": len(document.font_families),
        "sections": [section.kind.value for section in result.sections],
        "missing_sections": [kind.value for kind in result.missing_sections],
        "unrecognised_headings": sum(
            1 for section in result.sections if section.kind.value == "other"
        ),
        "skills_found": len(result.skills),
        "ats_score": result.ats.score,
        "failed_checks": [check.id for check in result.ats.checks if not check.passed],
        "roles_predicted": len(result.fit.predictions),
        "rubric_version": result.rubric_version,
    }
