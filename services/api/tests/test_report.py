import pymupdf
from fastapi.testclient import TestClient

from app.config import Settings
from app.pipeline.analysis import analyze_resume
from app.render.report_pdf import build_html, render_report

ENDPOINT = "/v1/report"
POSTING = "We need Python, Docker and Kubernetes."


def extracted_text(pdf: bytes) -> str:
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        return "".join(page.get_text() for page in document)


def test_report_is_a_readable_pdf_containing_the_score(
    single_column_pdf: bytes, settings: Settings
) -> None:
    result = analyze_resume(single_column_pdf, None, settings)

    pdf = render_report(result)

    assert pdf.startswith(b"%PDF")
    text = extracted_text(pdf)
    assert "Resume analysis report" in text
    assert str(round(result.ats.score)) in text
    assert result.ats.checks[0].label in text


def test_report_includes_job_match_only_when_one_was_given(
    single_column_pdf: bytes, settings: Settings
) -> None:
    without = analyze_resume(single_column_pdf, None, settings)
    with_posting = analyze_resume(single_column_pdf, POSTING, settings)

    assert "Target job match" not in build_html(without)
    assert "Target job match" in build_html(with_posting)


def test_report_escapes_markup_in_text(single_column_pdf: bytes, settings: Settings) -> None:
    result = analyze_resume(single_column_pdf, None, settings)
    check = result.ats.checks[0].model_copy(update={"label": "<b>x</b>&"})
    hostile = result.model_copy(update={"ats": result.ats.model_copy(update={"checks": [check]})})

    html = build_html(hostile)

    assert "&lt;b&gt;x&lt;/b&gt;&amp;" in html
    assert "<b>x</b>&" not in html


def test_endpoint_returns_a_downloadable_pdf(client: TestClient, single_column_pdf: bytes) -> None:
    upload = {"resume": ("resume.pdf", single_column_pdf, "application/pdf")}
    analysis = client.post("/v1/analyze", files=upload).json()

    response = client.post(ENDPOINT, json=analysis)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_endpoint_rejects_a_malformed_result(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={"analysis_id": "x"}).status_code == 422
