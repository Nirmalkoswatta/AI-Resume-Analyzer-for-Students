import pytest

from app.config import Settings
from app.pipeline.advise import advise
from app.pipeline.ats import evaluate, get_rubric
from app.pipeline.ingest import parse_document
from app.pipeline.segment import segment
from app.schemas.analysis import AtsScore
from app.schemas.enums import SectionKind, Severity


def score_of(payload: bytes, settings: Settings) -> AtsScore:
    document = parse_document(payload, settings)
    sections, _ = segment(document)
    return evaluate(document, sections)


def failed_ids(score: AtsScore) -> set[str]:
    return {check.id for check in score.checks if not check.passed}


def test_rubric_weights_sum_to_one() -> None:
    total = sum(definition.weight for definition in get_rubric().definitions.values())

    assert total == pytest.approx(1.0)


def test_every_check_has_both_explanations() -> None:
    for definition in get_rubric().definitions.values():
        assert definition.passed_explanation
        assert definition.failed_explanation
        assert definition.fix_title
        assert definition.fix_detail


def test_clean_resume_scores_full_marks(single_column_pdf: bytes, settings: Settings) -> None:
    score = score_of(single_column_pdf, settings)

    assert score.score == 100.0
    assert failed_ids(score) == set()


def test_two_column_layout_fails_its_check(two_column_pdf: bytes, settings: Settings) -> None:
    score = score_of(two_column_pdf, settings)

    assert "single_column_layout" in failed_ids(score)
    assert score.score < 100.0


def test_header_text_fails_its_check(header_footer_pdf: bytes, settings: Settings) -> None:
    assert "text_outside_header_footer" in failed_ids(score_of(header_footer_pdf, settings))


def test_creative_headings_fail_their_check(
    creative_headings_pdf: bytes, settings: Settings
) -> None:
    assert "recognisable_section_headings" in failed_ids(score_of(creative_headings_pdf, settings))


def test_every_check_is_explained(single_column_pdf: bytes, settings: Settings) -> None:
    score = score_of(single_column_pdf, settings)

    assert len(score.checks) == len(get_rubric().definitions)
    assert all(check.explanation for check in score.checks)


def test_scoring_is_deterministic(two_column_pdf: bytes, settings: Settings) -> None:
    first = score_of(two_column_pdf, settings)
    second = score_of(two_column_pdf, settings)

    assert first.score == second.score
    assert [check.passed for check in first.checks] == [check.passed for check in second.checks]


def test_failed_checks_become_suggestions(two_column_pdf: bytes, settings: Settings) -> None:
    score = score_of(two_column_pdf, settings)
    suggestions = advise(score, [], [])

    assert any(suggestion.id == "ats.single_column_layout" for suggestion in suggestions)


def test_passed_checks_produce_no_suggestions(single_column_pdf: bytes, settings: Settings) -> None:
    suggestions = advise(score_of(single_column_pdf, settings), [], [])

    assert suggestions == []


def test_missing_sections_become_suggestions(single_column_pdf: bytes, settings: Settings) -> None:
    suggestions = advise(score_of(single_column_pdf, settings), [SectionKind.SUMMARY], [])

    assert [suggestion.id for suggestion in suggestions] == ["section.summary"]
    assert suggestions[0].section is SectionKind.SUMMARY


def test_suggestions_are_ordered_by_severity(two_column_pdf: bytes, settings: Settings) -> None:
    order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
    suggestions = advise(
        score_of(two_column_pdf, settings), [SectionKind.SUMMARY, SectionKind.EDUCATION], []
    )
    ranks = [order[suggestion.severity] for suggestion in suggestions]

    assert ranks == sorted(ranks)


def test_multi_page_resume_fails_the_length_check(two_page_pdf: bytes, settings: Settings) -> None:
    assert "appropriate_length" in failed_ids(score_of(two_page_pdf, settings))
