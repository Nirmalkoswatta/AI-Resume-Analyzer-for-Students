import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.config import Settings

MAX_TRACKED_CLIENTS = 10_000
UNKNOWN_CLIENT = "unknown"
REDIS_KEY_PREFIX = "resume:ratelimit:"
ALLOWED = -1

logger = logging.getLogger("resume.ratelimit")

SLIDING_WINDOW_SCRIPT = """
local server_time = redis.call('TIME')
local now_ms = server_time[1] * 1000 + math.floor(server_time[2] / 1000)
local window_ms = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_ms - window_ms)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil(tonumber(oldest[2]) + window_ms - now_ms))
end
redis.call('ZADD', KEYS[1], now_ms, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window_ms)
return -1
"""


class Limiter(Protocol):
    def check(self, key: str, now: float) -> float | None: ...


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


class RedisSlidingWindowLimiter:
    """Shares one window per client across every API instance.

    Fails open: if Redis is unreachable the request is allowed and the error is logged,
    because a cache outage should not lock students out of their own resume.
    """

    def __init__(self, client: Redis, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.client = client
        self.script = client.register_script(SLIDING_WINDOW_SCRIPT)

    def check(self, key: str, now: float) -> float | None:  # noqa: ARG002
        try:
            retry_after_ms = int(
                self.script(
                    keys=[REDIS_KEY_PREFIX + key],
                    args=[self.limit, int(self.window_seconds * 1000), uuid4().hex],
                )
            )
        except RedisError:
            logger.exception("ratelimit.backend_unavailable")
            return None

        return None if retry_after_ms == ALLOWED else retry_after_ms / 1000


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


def build_limiter(settings: Settings) -> Limiter:
    window_seconds = float(settings.rate_limit_window_seconds)
    if settings.redis_url:
        return RedisSlidingWindowLimiter(
            Redis.from_url(settings.redis_url, socket_timeout=1.0, socket_connect_timeout=1.0),
            limit=settings.rate_limit_requests,
            window_seconds=window_seconds,
        )
    return SlidingWindowLimiter(limit=settings.rate_limit_requests, window_seconds=window_seconds)


def monotonic_now() -> float:
    return time.monotonic()
