import io
from html import escape

import pymupdf

from app.schemas.analysis import AnalysisResult
from app.schemas.enums import EvidenceStrength

PAGE_MARGIN = 48
MAX_LISTED_SKILLS = 60

REPORT_CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #1a1a1a; }
h1 { font-size: 20pt; margin-bottom: 2pt; }
h2 { font-size: 13pt; margin-top: 16pt; margin-bottom: 4pt; color: #0b4f9c; }
p { margin-top: 2pt; margin-bottom: 4pt; }
.muted { color: #666666; }
.score { font-size: 28pt; font-weight: bold; }
.pass { color: #1b7a3d; }
.fail { color: #b3261e; }
li { margin-bottom: 3pt; }
"""


def render_report(result: AnalysisResult) -> bytes:
    """Renders the analysis as a paginated A4 PDF. The result is trusted to be schema-valid."""
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    story = pymupdf.Story(html=build_html(result), user_css=REPORT_CSS)

    page = pymupdf.paper_rect("a4")
    body = pymupdf.Rect(
        page.x0 + PAGE_MARGIN, page.y0 + PAGE_MARGIN, page.x1 - PAGE_MARGIN, page.y1 - PAGE_MARGIN
    )
    has_more = True
    while has_more:
        device = writer.begin_page(page)
        has_more, _ = story.place(body)
        story.draw(device)
        writer.end_page()
    writer.close()

    return buffer.getvalue()


def build_html(result: AnalysisResult) -> str:
    return "".join(
        [
            header_html(result),
            suggestions_html(result),
            checks_html(result),
            sections_html(result),
            skills_html(result),
            fit_html(result),
        ]
    )


def header_html(result: AnalysisResult) -> str:
    stats = result.document
    return (
        "<h1>Resume analysis report</h1>"
        f'<p class="muted">{stats.page_count} page(s), {stats.word_count} words, '
        f"{stats.column_count} column(s). Rubric {escape(result.rubric_version)}.</p>"
        f'<p class="score">{round(result.ats.score)}<span class="muted"> / 100</span> '
        '<span class="muted">ATS score</span></p>'
    )


def suggestions_html(result: AnalysisResult) -> str:
    if not result.suggestions:
        return "<h2>What to fix</h2><p>Nothing to fix. This resume passes every check.</p>"

    items = "".join(
        f"<li><b>[{item.severity.value.upper()}] {escape(item.title)}</b><br>"
        f"{escape(item.detail)}</li>"
        for item in result.suggestions
    )
    return f"<h2>What to fix</h2><ul>{items}</ul>"


def checks_html(result: AnalysisResult) -> str:
    items = "".join(
        f'<li><b class="{"pass" if check.passed else "fail"}">'
        f"{'PASS' if check.passed else 'FAIL'}</b> {escape(check.label)}"
        f'<br><span class="muted">{escape(check.explanation)}</span></li>'
        for check in result.ats.checks
    )
    return f"<h2>ATS checks</h2><ul>{items}</ul>"


def sections_html(result: AnalysisResult) -> str:
    found = ", ".join(escape(section.kind.value) for section in result.sections) or "none"
    missing = ", ".join(escape(kind.value) for kind in result.missing_sections) or "none"
    return f"<h2>Sections</h2><p><b>Found:</b> {found}</p><p><b>Missing:</b> {missing}</p>"


def skills_html(result: AnalysisResult) -> str:
    def names(strength: EvidenceStrength) -> str:
        chosen = [skill.name for skill in result.skills if skill.evidence is strength]
        return ", ".join(escape(name) for name in chosen[:MAX_LISTED_SKILLS]) or "none"

    return (
        "<h2>Skills</h2>"
        f"<p><b>Demonstrated:</b> {names(EvidenceStrength.DEMONSTRATED)}</p>"
        f"<p><b>Claimed only:</b> {names(EvidenceStrength.CLAIMED)}</p>"
    )


def fit_html(result: AnalysisResult) -> str:
    roles = "".join(
        f"<li>{escape(prediction.role)} ({round(prediction.confidence * 100)}%)</li>"
        for prediction in result.fit.predictions
    )
    html = f"<h2>Role fit</h2><ul>{roles or '<li>No roles matched.</li>'}</ul>"

    match = result.fit.job_description
    if match is None:
        return html

    matched = ", ".join(escape(skill) for skill in match.matched_skills) or "none"
    missing = ", ".join(escape(gap.skill) for gap in match.missing_skills) or "none"
    return (
        html + "<h2>Target job match</h2>"
        f"<p><b>Similarity:</b> {round(match.similarity * 100)}%</p>"
        f"<p><b>Matched:</b> {matched}</p><p><b>Missing:</b> {missing}</p>"
    )
