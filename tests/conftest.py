import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Never load a developer's database or JWT key into the test application.
os.environ["SECRET_KEY"] = "test-only-signing-key-do-not-use-in-production-123456"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"
os.environ["LOGIN_RATE_LIMIT"] = "10"
os.environ["REGISTER_RATE_LIMIT"] = "5"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"

from app.core.config import PROJECT_ROOT, get_settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.middlewares.rate_limit import get_rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_rate_limits():
    get_rate_limiter.cache_clear()
    yield
    get_rate_limiter.cache_clear()


@pytest.fixture
def db_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def db(db_engine):
    with sessionmaker(bind=db_engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(db_engine, monkeypatch):
    sessions = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_db():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.main.engine", db_engine)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_data():
    return {
        "username": "starter_user",
        "email": "starter@example.com",
        "password": "safe-password-123",
    }


@pytest.fixture
def registered_user(client, user_data):
    response = client.post("/register", json=user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def token(client, registered_user, user_data):
    response = client.post(
        "/token", data={"username": user_data["username"], "password": user_data["password"]}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
