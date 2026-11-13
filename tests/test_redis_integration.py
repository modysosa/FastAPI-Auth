"""Exercise the real Redis backend; CI provisions its disposable Redis service."""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.middlewares.rate_limit import check_rate_limit, get_rate_limiter

pytestmark = [
    pytest.mark.redis,
    pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="TEST_REDIS_URL is not set"),
]


@pytest.fixture
def redis_backend(db_engine, monkeypatch):
    # Isolate keys without flushing or deleting unrelated data in the Redis DB.
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", os.environ["TEST_REDIS_URL"])
    monkeypatch.setenv("RATE_LIMIT_PREFIX", f"integration-{uuid4().hex}")
    monkeypatch.setenv("REGISTER_RATE_LIMIT", "3")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    get_rate_limiter.cache_clear()
    yield
    get_rate_limiter.cache_clear()
    get_settings.cache_clear()


def test_workers_share_the_same_budget(redis_backend):
    assert check_rate_limit("/register", "192.0.2.1") is None
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.middlewares.rate_limit import check_rate_limit; "
                "assert check_rate_limit('/register', '192.0.2.1') is None; "
                "assert check_rate_limit('/register', '192.0.2.1') is None"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert check_rate_limit("/register", "192.0.2.1") is not None
    assert check_rate_limit("/register", "192.0.2.2") is None


def test_redis_increments_are_atomic(redis_backend):
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(lambda _: check_rate_limit("/register", "192.0.2.3"), range(20))
        )
    assert results.count(None) == 3


def test_redis_window_expires(redis_backend, monkeypatch):
    monkeypatch.setenv("REGISTER_RATE_LIMIT", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "1")
    get_settings.cache_clear()
    assert check_rate_limit("/register", "192.0.2.4") is None
    assert check_rate_limit("/register", "192.0.2.4") is not None
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        time.sleep(0.05)
        if check_rate_limit("/register", "192.0.2.4") is None:
            break
    else:
        pytest.fail("Redis did not release the budget after the window expired")


def test_redis_limit_is_enforced_over_http(client, redis_backend):
    for _ in range(3):
        assert client.post("/register", json={}).status_code == 422
    response = client.post("/register", json={})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1
