from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.routers.analyze import get_limiter
from tests import pdf_builder

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    get_limiter.cache_clear()
    yield
    get_limiter.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def sample_resume() -> bytes:
    return (FIXTURES / "sample_resume.pdf").read_bytes()


@pytest.fixture
def single_column_pdf() -> bytes:
    return pdf_builder.single_column_resume()


@pytest.fixture
def two_column_pdf() -> bytes:
    return pdf_builder.two_column_resume()


@pytest.fixture
def header_footer_pdf() -> bytes:
    return pdf_builder.resume_with_header_footer_text()


@pytest.fixture
def edge_text_pdf() -> bytes:
    return pdf_builder.single_page_with_edge_text()


@pytest.fixture
def creative_headings_pdf() -> bytes:
    return pdf_builder.resume_with_creative_headings()


@pytest.fixture
def scanned_pdf() -> bytes:
    return pdf_builder.scanned_resume()


@pytest.fixture
def encrypted_pdf() -> bytes:
    return pdf_builder.encrypted_resume()


@pytest.fixture
def two_page_pdf() -> bytes:
    return pdf_builder.multi_page_resume(2)


@pytest.fixture
def twelve_page_pdf() -> bytes:
    return pdf_builder.multi_page_resume(12)


@pytest.fixture
def ambiguous_skills_pdf() -> bytes:
    return pdf_builder.resume_with_ambiguous_skills()


@pytest.fixture
def misspelled_skills_pdf() -> bytes:
    return pdf_builder.resume_with_misspelled_skills()


@pytest.fixture
def scrambled_order_pdf() -> bytes:
    return pdf_builder.scrambled_block_order_resume()


@pytest.fixture
def banner_over_columns_pdf() -> bytes:
    return pdf_builder.two_column_resume_under_full_width_banner()


@pytest.fixture
def title_case_headings_pdf() -> bytes:
    return pdf_builder.resume_with_title_case_headings()
