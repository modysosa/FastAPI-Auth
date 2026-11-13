import logging

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import inspect

from app.core.config import PROJECT_ROOT, Settings
from app.main import app


def test_health_and_readiness(client, db_engine):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    with db_engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE users")
    assert client.get("/health/ready").status_code == 503


def test_cors_allows_only_configured_origin(client):
    def preflight(origin):
        return client.options(
            "/token",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    allowed = preflight("http://localhost:3000")
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in preflight("https://untrusted.example").headers


@pytest.mark.parametrize("secret", ["", "short"])
def test_insecure_secret_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key=secret)


def test_missing_secret_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_migration_roundtrip_and_metadata_match(db_engine):
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.check(config)
    command.downgrade(config, "base")
    assert "users" not in inspect(db_engine).get_table_names()
    command.upgrade(config, "head")
    assert "users" in inspect(db_engine).get_table_names()


def test_logs_omit_password_tokens_and_query_strings(client, user_data, caplog):
    with caplog.at_level(logging.INFO, logger="app"):
        client.post("/register?private=hidden-value", json=user_data)
    messages = " ".join(record.getMessage() for record in caplog.records if record.name == "app")
    assert user_data["password"] not in messages
    assert "hidden-value" not in messages
    assert "POST /register status=201" in messages


def test_unhandled_error_is_generic_with_cors_and_safe_logs(client, caplog):
    from app.database import get_db

    def broken_db():
        raise RuntimeError("secret-database-password")

    app.dependency_overrides[get_db] = broken_db
    with caplog.at_level(logging.ERROR, logger="app"):
        response = client.post(
            "/token",
            data={"username": "user", "password": "secret"},
            headers={"Origin": "http://localhost:3000"},
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "secret-database-password" not in caplog.text
