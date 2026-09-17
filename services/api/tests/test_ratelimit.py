from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.config import Settings
from app.ratelimit import (
    MAX_TRACKED_CLIENTS,
    SlidingWindowLimiter,
    build_limiter,
    client_key,
)
from app.routers.analyze import get_limiter
from app.schemas.enums import AnalysisErrorCode

ENDPOINT = "/v1/analyze"


def request_with(headers: dict[str, str], peer: str | None) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": (peer, 12345) if peer else None,
    }
    return Request(scope)


def test_allows_up_to_the_limit() -> None:
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60.0)

    assert [limiter.check("a", 0.0) for _ in range(3)] == [None, None, None]


def test_blocks_past_the_limit_and_reports_wait() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60.0)
    limiter.check("a", 0.0)
    limiter.check("a", 10.0)

    retry_after = limiter.check("a", 20.0)

    assert retry_after == pytest.approx(40.0)


def test_window_slides_so_old_hits_expire() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60.0)
    limiter.check("a", 0.0)
    limiter.check("a", 1.0)

    assert limiter.check("a", 30.0) is not None
    assert limiter.check("a", 62.0) is None


def test_clients_are_tracked_separately() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60.0)
    limiter.check("a", 0.0)

    assert limiter.check("b", 0.0) is None
    assert limiter.check("a", 0.0) is not None


def test_expired_clients_are_evicted() -> None:
    limiter = SlidingWindowLimiter(limit=5, window_seconds=10.0)
    for index in range(MAX_TRACKED_CLIENTS + 1):
        limiter.check(f"client-{index}", 0.0)

    limiter.check("late", 1000.0)

    assert len(limiter.hits) < MAX_TRACKED_CLIENTS


def test_socket_peer_used_when_no_proxy_trusted() -> None:
    request = request_with({"x-forwarded-for": "1.2.3.4"}, peer="10.0.0.1")

    assert client_key(request, trusted_proxy_count=0) == "10.0.0.1"


def test_forwarded_header_used_when_proxy_trusted() -> None:
    behind_one_proxy = request_with({"x-forwarded-for": "1.2.3.4"}, peer="10.0.0.7")

    assert client_key(behind_one_proxy, trusted_proxy_count=1) == "1.2.3.4"


def test_client_cannot_spoof_a_different_identity() -> None:
    spoofed = request_with({"x-forwarded-for": "9.9.9.9, 1.2.3.4"}, peer="10.0.0.7")

    assert client_key(spoofed, trusted_proxy_count=1) == "1.2.3.4"


def test_client_cannot_shorten_the_chain_to_reach_the_socket_peer() -> None:
    truncated = request_with({"x-forwarded-for": "9.9.9.9"}, peer="10.0.0.7")

    assert client_key(truncated, trusted_proxy_count=2) == "10.0.0.7"


def test_two_trusted_proxies_select_the_original_client() -> None:
    chained = request_with({"x-forwarded-for": "1.2.3.4, 172.16.0.1"}, peer="10.0.0.7")

    assert client_key(chained, trusted_proxy_count=2) == "1.2.3.4"


def test_missing_client_falls_back_to_unknown() -> None:
    assert client_key(request_with({}, peer=None), trusted_proxy_count=0) == "unknown"


def test_limiter_reads_configured_limits() -> None:
    limiter = build_limiter(Settings(rate_limit_requests=4, rate_limit_window_seconds=90))

    assert limiter.limit == 4
    assert limiter.window_seconds == 90.0


def test_endpoint_returns_429_once_exhausted(
    client: TestClient, single_column_pdf: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_limiter(), "limit", 2)
    upload = {"resume": ("resume.pdf", single_column_pdf, "application/pdf")}

    assert client.post(ENDPOINT, files=upload).status_code == 200
    assert client.post(ENDPOINT, files=upload).status_code == 200

    blocked = client.post(ENDPOINT, files=upload)

    assert blocked.status_code == 429
    assert blocked.json()["code"] == AnalysisErrorCode.RATE_LIMITED
    assert blocked.json()["remediation"]
    assert int(blocked.headers["retry-after"]) >= 1


def test_health_is_not_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_limiter(), "limit", 1)

    assert all(client.get("/v1/health").status_code == 200 for _ in range(5))
