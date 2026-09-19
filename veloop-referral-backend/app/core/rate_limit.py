"""Fixed-window rate limiter.

Uses Redis when REDIS_URL is configured (multi-instance safe), otherwise an
in-process store. Applied as a FastAPI dependency on sensitive endpoints.
"""
import time
from threading import Lock
from typing import Dict, Optional, Tuple

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError, ErrorCode

_memory: Dict[str, Tuple[int, float]] = {}
_lock = Lock()

_redis = None
if settings.REDIS_URL:  # pragma: no cover - optional infra
    try:
        import redis  # type: ignore

        _redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        _redis = None


def parse_rule(rule: str) -> Tuple[int, int]:
    times, _, seconds = rule.partition("/")
    return int(times), int(seconds)


def _hit(key: str, limit: int, window: int) -> bool:
    """Returns True when the request is allowed."""
    if _redis is not None:  # pragma: no cover
        count = _redis.incr(key)
        if count == 1:
            _redis.expire(key, window)
        return count <= limit
    now = time.time()
    with _lock:
        count, reset = _memory.get(key, (0, now + window))
        if now > reset:
            count, reset = 0, now + window
        count += 1
        _memory[key] = (count, reset)
        return count <= limit


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimit:
    """Dependency: `Depends(RateLimit(settings.RATE_LIMIT_AUTH, "auth"))`."""

    def __init__(self, rule: str, scope: str, by_user: bool = False):
        self.limit, self.window = parse_rule(rule)
        self.scope = scope
        self.by_user = by_user

    async def __call__(self, request: Request) -> None:
        identity: Optional[str] = None
        if self.by_user:
            auth = request.headers.get("authorization", "")
            identity = auth[-24:] if auth else None
        identity = identity or client_ip(request)
        key = f"rl:{self.scope}:{identity}:{int(time.time() // self.window)}"
        if not _hit(key, self.limit, self.window):
            raise AppError(
                ErrorCode.RATE_LIMITED,
                "Too many requests. Please slow down and try again shortly.",
                429,
            )


def reset_rate_limits() -> None:
    """Test helper."""
    with _lock:
        _memory.clear()
