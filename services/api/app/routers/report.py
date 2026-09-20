from fastapi import APIRouter
from fastapi.responses import Response

from app.render.report_pdf import render_report
from app.schemas.analysis import AnalysisResult

router = APIRouter(tags=["report"])

PDF_MEDIA_TYPE = "application/pdf"


@router.post(
    "/report",
    response_class=Response,
    responses={200: {"content": {PDF_MEDIA_TYPE: {}}, "description": "The report as a PDF."}},
)
async def report(result: AnalysisResult) -> Response:
    return Response(
        content=render_report(result),
        media_type=PDF_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="resume-report.pdf"'},
    )
