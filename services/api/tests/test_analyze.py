from fastapi.testclient import TestClient

from app.config import get_settings
from app.schemas.enums import AnalysisErrorCode

ENDPOINT = "/v1/analyze"


def upload(payload: bytes, content_type: str = "application/pdf") -> dict[str, object]:
    return {"resume": ("resume.pdf", payload, content_type)}


def test_health_reports_versions(client: TestClient) -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["models_loaded"] is True
    assert body["schema_version"]


def test_analyze_returns_full_result(client: TestClient, minimal_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(minimal_pdf))

    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["ats"]["score"] <= 100.0
    assert body["ats"]["checks"]
    assert body["sections"]
    assert body["suggestions"]
    assert body["fit"]["predictions"]


def test_job_description_absent_by_default(client: TestClient, minimal_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(minimal_pdf))

    assert response.json()["fit"]["job_description"] is None


def test_job_description_produces_gap_analysis(client: TestClient, minimal_pdf: bytes) -> None:
    response = client.post(
        ENDPOINT,
        files=upload(minimal_pdf),
        data={"job_description": "We are hiring a graduate backend engineer."},
    )

    match = response.json()["fit"]["job_description"]
    assert match is not None
    assert match["missing_skills"]


def test_docx_renamed_to_pdf_is_rejected(client: TestClient) -> None:
    response = client.post(ENDPOINT, files=upload(b"PK\x03\x04 not really a pdf"))

    assert response.status_code == 415
    assert response.json()["code"] == AnalysisErrorCode.UNSUPPORTED_MEDIA_TYPE


def test_non_pdf_content_type_is_rejected(client: TestClient, minimal_pdf: bytes) -> None:
    response = client.post(ENDPOINT, files=upload(minimal_pdf, content_type="image/png"))

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
