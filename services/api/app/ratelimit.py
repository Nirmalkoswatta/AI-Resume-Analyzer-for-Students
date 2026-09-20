import time
from collections import deque
from dataclasses import dataclass, field

from fastapi import Request

from app.config import Settings

MAX_TRACKED_CLIENTS = 10_000
UNKNOWN_CLIENT = "unknown"


@dataclass
class SlidingWindowLimiter:
    limit: int
    window_seconds: float
    hits: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, key: str, now: float) -> float | None:
        recent = self.hits.setdefault(key, deque())
        cutoff = now - self.window_seconds

        while recent and recent[0] <= cutoff:
            recent.popleft()

        if len(recent) >= self.limit:
            return recent[0] + self.window_seconds - now

        recent.append(now)
        if len(self.hits) > MAX_TRACKED_CLIENTS:
            self.evict_expired(cutoff)
        return None

    def evict_expired(self, cutoff: float) -> None:
        stale = [key for key, recent in self.hits.items() if not recent or recent[-1] <= cutoff]
        for key in stale:
            del self.hits[key]


def client_key(request: Request, trusted_proxy_count: int) -> str:
    if trusted_proxy_count > 0:
        chain = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(chain) >= trusted_proxy_count:
            return chain[-trusted_proxy_count]

    return request.client.host if request.client else UNKNOWN_CLIENT


def build_limiter(settings: Settings) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=float(settings.rate_limit_window_seconds),
    )


def monotonic_now() -> float:
    return time.monotonic()
