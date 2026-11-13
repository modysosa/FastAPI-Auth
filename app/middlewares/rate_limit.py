import hashlib
import hmac
import logging
import math
import time
from functools import lru_cache
from threading import Lock

from limits import RateLimitItemPerSecond
from limits.errors import StorageError
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter
from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger("app")
_initialization_lock = Lock()


@lru_cache
def get_rate_limiter() -> FixedWindowRateLimiter:
    uri = get_settings().rate_limit_storage_uri.get_secret_value()
    options = {} if uri == "memory://" else {"socket_connect_timeout": 1, "socket_timeout": 1}
    return FixedWindowRateLimiter(storage_from_string(uri, **options))


def check_rate_limit(path: str, client_host: str) -> int | None:
    settings = get_settings()
    amount = settings.login_rate_limit if path == "/token" else settings.register_rate_limit
    rule = RateLimitItemPerSecond(amount, settings.rate_limit_window_seconds)
    # Store a keyed digest, rather than a raw client IP, in the backend.
    identity = hmac.new(
        settings.secret_key.get_secret_value().encode(), client_host.encode(), hashlib.sha256
    ).hexdigest()
    # lru_cache can invoke its factory twice on concurrent cache misses.
    with _initialization_lock:
        limiter = get_rate_limiter()
    key = (settings.rate_limit_prefix, path, identity)
    if limiter.hit(rule, *key):
        return None
    window = limiter.get_window_stats(rule, *key)
    return max(1, math.ceil(window.reset_time - time.time()))


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Count requests before form/JSON parsing and password hashing. Redirects
        # from trailing-slash URLs are counted only at the canonical destination.
        if request.method != "POST" or request.url.path not in {"/token", "/register"}:
            return await call_next(request)
        client_host = request.client.host if request.client else "unknown"
        try:
            retry_after = await run_in_threadpool(check_rate_limit, request.url.path, client_host)
        except (StorageError, RedisError):
            # Fail closed if a configured shared backend is unavailable.
            logger.error("rate_limit_storage_unavailable")
            return JSONResponse(
                status_code=503,
                content={"detail": "Authentication temporarily unavailable"},
                headers={"Retry-After": "5", "Cache-Control": "no-store"},
            )
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
            )
        return await call_next(request)
