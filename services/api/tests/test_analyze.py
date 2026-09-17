from typing import Any

from fastapi.testclient import TestClient

from app.config import get_settings
from app.schemas.enums import AnalysisErrorCode

ENDPOINT = "/v1/analyze"


def upload(payload: bytes, content_type: str = "application/pdf") -> dict[str, Any]:
    return {"resume": ("resume.pdf", payload, content_type)}


def test_health_reports_versions(client: TestClient) -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["schema_version"]


def test_analyze_returns_full_result(client: TestClient, single_column_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(single_column_pdf))

    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["ats"]["score"] <= 100.0
    assert body["ats"]["checks"]
    assert body["sections"]
    assert body["fit"]["predictions"]
    assert body["document"]["page_count"] == 1


def test_document_stats_reflect_the_real_file(client: TestClient, two_column_pdf: bytes) -> None:
    body = client.post(ENDPOINT, files=upload(two_column_pdf)).json()

    assert body["document"]["column_count"] == 2
    assert body["document"]["machine_readable"] is True
    assert body["document"]["font_families"]


def test_sections_come_from_the_uploaded_file(
    client: TestClient, creative_headings_pdf: bytes
) -> None:
    body = client.post(ENDPOINT, files=upload(creative_headings_pdf)).json()

    assert "other" in [section["kind"] for section in body["sections"]]


def test_identical_uploads_score_identically(client: TestClient, two_column_pdf: bytes) -> None:
    first = client.post(ENDPOINT, files=upload(two_column_pdf)).json()
    second = client.post(ENDPOINT, files=upload(two_column_pdf)).json()

    assert first["ats"] == second["ats"]
    assert first["sections"] == second["sections"]
    assert first["analysis_id"] != second["analysis_id"]


def test_job_description_absent_by_default(client: TestClient, single_column_pdf: bytes) -> None:
    body = client.post(ENDPOINT, files=upload(single_column_pdf)).json()

    assert body["fit"]["job_description"] is None


def test_job_description_produces_gap_analysis(
    client: TestClient, single_column_pdf: bytes
) -> None:
    response = client.post(
        ENDPOINT,
        files=upload(single_column_pdf),
        data={"job_description": "Graduate backend role using Python, Docker and Kubernetes."},
    )

    match = response.json()["fit"]["job_description"]
    assert match is not None
    assert match["missing_skills"]


def test_scanned_resume_is_rejected(client: TestClient, scanned_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(scanned_pdf))

    assert response.status_code == 422
    assert response.json()["code"] == AnalysisErrorCode.NOT_MACHINE_READABLE


def test_encrypted_resume_is_rejected(client: TestClient, encrypted_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(encrypted_pdf))

    assert response.status_code == 422
    assert response.json()["code"] == AnalysisErrorCode.ENCRYPTED_PDF


def test_long_document_is_rejected(client: TestClient, twelve_page_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(twelve_page_pdf))

    assert response.status_code == 422
    assert response.json()["code"] == AnalysisErrorCode.TOO_MANY_PAGES


def test_corrupt_pdf_is_rejected(client: TestClient) -> None:
    response = client.post(ENDPOINT, files=upload(b"%PDF-1.4 not actually a pdf"))

    assert response.status_code == 422
    assert response.json()["code"] == AnalysisErrorCode.CORRUPT_PDF


def test_docx_renamed_to_pdf_is_rejected(client: TestClient) -> None:
    response = client.post(ENDPOINT, files=upload(b"PK\x03\x04 not really a pdf"))

    assert response.status_code == 415
    assert response.json()["code"] == AnalysisErrorCode.UNSUPPORTED_MEDIA_TYPE


def test_non_pdf_content_type_is_rejected(client: TestClient, single_column_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(single_column_pdf, content_type="image/png"))

    assert response.status_code == 415


def test_empty_upload_is_rejected(client: TestClient) -> None:
    response = client.post(ENDPOINT, files=upload(b""))

    assert response.status_code == 422
    assert response.json()["code"] == AnalysisErrorCode.EMPTY_DOCUMENT


def test_oversized_upload_is_rejected(client: TestClient) -> None:
    oversized = b"%PDF-1.4\n" + b"0" * (get_settings().max_upload_bytes + 1)

    response = client.post(ENDPOINT, files=upload(oversized))

    assert response.status_code == 413
    assert response.json()["code"] == AnalysisErrorCode.FILE_TOO_LARGE


def test_errors_carry_remediation(client: TestClient) -> None:
    response = client.post(ENDPOINT, files=upload(b"PK\x03\x04"))

    assert response.json()["remediation"]
