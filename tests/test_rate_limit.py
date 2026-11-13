from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.core.config import Settings
from app.main import app
from app.middlewares.rate_limit import check_rate_limit, get_rate_limiter


@pytest.mark.parametrize("path,limit", [("/token", 10), ("/register", 5)])
def test_auth_endpoints_are_limited_before_validation(client, path, limit):
    for _ in range(limit):
        assert client.post(path, json={}).status_code == 422
    response = client.post(path, json={}, headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= 60
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-expose-headers"] == "Retry-After"


def test_limits_are_independent_and_health_remains_available(client):
    for _ in range(6):
        client.post("/register", json={})
    assert client.post("/token", json={}).status_code == 422
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_successful_requests_count_too(client, user_data):
    assert client.post("/register", json=user_data).status_code == 201
    for _ in range(4):
        assert client.post("/register", json={}).status_code == 422
    assert client.post("/register", json={}).status_code == 429


def test_forwarded_headers_cannot_bypass_limit(client):
    for i in range(5):
        assert (
            client.post(
                "/register", json={}, headers={"X-Forwarded-For": f"192.0.2.{i}"}
            ).status_code
            == 422
        )
    assert (
        client.post("/register", json={}, headers={"X-Forwarded-For": "192.0.2.99"}).status_code
        == 429
    )


def test_client_ips_have_independent_limits(client):
    for _ in range(6):
        client.post("/register", json={})
    with TestClient(app, client=("192.0.2.10", 50000)) as other_client:
        assert other_client.post("/register", json={}).status_code == 422


def test_trailing_slash_redirect_does_not_double_count(client):
    for _ in range(5):
        assert client.post("/register/", json={}).status_code == 422
    assert client.post("/register/", json={}).status_code == 429


def test_expired_window_allows_requests_again(client, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("time.time", lambda: clock[0])
    for _ in range(5):
        assert client.post("/register", json={}).status_code == 422
    assert client.post("/register", json={}).status_code == 429
    clock[0] += 61
    assert client.post("/register", json={}).status_code == 422


def test_concurrent_requests_cannot_exceed_limit(db_engine):
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(lambda _: check_rate_limit("/register", "192.0.2.20"), range(20))
        )
    assert results.count(None) == 5


def test_storage_failure_fails_closed_without_leaking_credentials(client, monkeypatch, caplog):
    def unavailable(*args, **kwargs):
        raise ConnectionError("redis://user:secret-password@example:6379")

    monkeypatch.setattr(get_rate_limiter(), "hit", unavailable)
    response = client.post("/token", json={})
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert "secret-password" not in response.text + caplog.text
    assert client.get("/health").status_code == 200


def test_limits_are_configurable(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("REGISTER_RATE_LIMIT", "1")
    get_settings.cache_clear()
    assert client.post("/register", json={}).status_code == 422
    assert client.post("/register", json={}).status_code == 429


@pytest.mark.parametrize(
    "changes",
    [
        {"login_rate_limit": 0},
        {"register_rate_limit": -1},
        {"rate_limit_window_seconds": 0},
        {"rate_limit_storage_uri": "unsupported://"},
    ],
)
def test_invalid_configuration_rejected(changes):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **changes)
