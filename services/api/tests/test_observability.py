import json
import logging

from fastapi.testclient import TestClient

from app.config import Settings
from app.observability import (
    REQUEST_ID_HEADER,
    JsonFormatter,
    describe_analysis,
    new_request_id,
)
from app.pipeline.analysis import analyze_resume

ENDPOINT = "/v1/analyze"


def formatted(record: logging.LogRecord) -> dict[str, object]:
    parsed: dict[str, object] = json.loads(JsonFormatter().format(record))
    return parsed


def record_with(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("resume.test", logging.INFO, "f.py", 1, "some.event", None, None)
    record.__dict__.update(extra)
    return record


def test_log_lines_are_valid_json_with_core_fields() -> None:
    payload = formatted(record_with())

    assert payload["event"] == "some.event"
    assert payload["level"] == "info"
    assert payload["logger"] == "resume.test"
    assert payload["ts"]


def test_extra_fields_are_merged_into_the_payload() -> None:
    payload = formatted(record_with(ats_score=48.0, pages=2))

    assert payload["ats_score"] == 48.0
    assert payload["pages"] == 2


def test_exceptions_are_recorded_with_type_and_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "resume.test", logging.ERROR, "f.py", 1, "failed", None, sys.exc_info()
        )

    payload = formatted(record)

    assert payload["error_type"] == "ValueError"
    assert "ValueError" in str(payload["traceback"])


def test_generated_request_ids_are_unique() -> None:
    assert new_request_id(None) != new_request_id(None)


def test_supplied_request_id_is_honoured() -> None:
    assert new_request_id("abc-123_XYZ") == "abc-123_XYZ"


def test_supplied_request_id_is_sanitised() -> None:
    assert new_request_id("../../etc/passwd\n<script>") == "etcpasswdscript"


def test_absurd_request_id_is_truncated() -> None:
    assert len(new_request_id("a" * 500)) == 64


def test_blank_request_id_falls_back_to_a_generated_one() -> None:
    assert new_request_id("!!!")


def test_response_carries_the_request_id(client: TestClient, single_column_pdf: bytes) -> None:
    response = client.post(
        ENDPOINT, files={"resume": ("r.pdf", single_column_pdf, "application/pdf")}
    )

    assert response.headers[REQUEST_ID_HEADER]


def test_supplied_request_id_is_echoed_back(client: TestClient, single_column_pdf: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files={"resume": ("r.pdf", single_column_pdf, "application/pdf")},
        headers={REQUEST_ID_HEADER: "trace-42"},
    )

    assert response.headers[REQUEST_ID_HEADER] == "trace-42"


def test_errors_also_carry_the_request_id(client: TestClient) -> None:
    response = client.post(ENDPOINT, files={"resume": ("r.pdf", b"PK nope", "application/pdf")})

    assert response.status_code == 415
    assert response.headers[REQUEST_ID_HEADER]


def test_analysis_log_describes_shape_not_content(
    single_column_pdf: bytes, settings: Settings
) -> None:
    result = analyze_resume(single_column_pdf, "Python and Docker role", settings)
    serialised = json.dumps(describe_analysis(result))

    assert "Priya" not in serialised
    assert "example.com" not in serialised
    assert "Reddy Labs" not in serialised
    assert "Colombo" not in serialised
    for skill in result.skills:
        assert skill.name not in serialised


def test_analysis_log_keeps_what_is_needed_to_diagnose(
    two_column_pdf: bytes, settings: Settings
) -> None:
    described = describe_analysis(analyze_resume(two_column_pdf, None, settings))

    assert described["columns"] == 2
    assert "single_column_layout" in described["failed_checks"]
    assert described["pages"] == 1
    assert "skills_found" in described


def test_a_block_with_no_heading_is_not_counted_as_an_unrecognised_heading(
    unlabelled_main_column_pdf: bytes, settings: Settings
) -> None:
    result = analyze_resume(unlabelled_main_column_pdf, None, settings)
    payload = describe_analysis(result)

    assert payload["unrecognised_headings"] == 0
    assert payload["unlabelled_blocks"] == 1
