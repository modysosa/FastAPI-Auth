from datetime import timedelta

import pytest
from jose import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.models.user_model import UserInDB
from app.schemas.user_schema import UserCreate
from app.services.auth_service import UserAlreadyExistsError, register_user_in_db
from app.utils.security import create_access_token, verify_password


def test_register_hashes_password_and_returns_only_public_fields(client, db, user_data):
    response = client.post("/register", json=user_data)
    assert response.status_code == 201
    assert set(response.json()) == {"id", "username", "email", "admin", "disabled"}
    assert response.json()["admin"] is False
    assert response.json()["disabled"] is False
    user = db.scalar(select(UserInDB))
    assert user.hashed_password != user_data["password"]
    assert verify_password(user_data["password"], user.hashed_password)


@pytest.mark.parametrize("field", ["username", "email"])
def test_duplicate_identity_is_case_insensitive(client, registered_user, user_data, field):
    duplicate = {**user_data, "username": "another_user", "email": "other@example.com"}
    duplicate[field] = user_data[field].upper()
    assert client.post("/register", json=duplicate).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"password": None},
        {"password": ""},
        {"password": "short"},
        {"password": "a" * 73},
        {"password": "\u00e9" * 37},
        {"password": " " * 8},
        {"email": "invalid"},
        {"email": None},
        {"username": ""},
        {"username": "ab"},
        {"username": "a@b.com"},
        {"admin": True},
        {"disabled": True},
    ],
)
def test_registration_validation(client, user_data, changes):
    response = client.post("/register", json={**user_data, **changes})
    assert response.status_code == 422
    for error in response.json()["detail"]:
        assert "input" not in error
        assert "ctx" not in error


def test_missing_password_and_nested_password_are_not_echoed(client, user_data):
    user_data.pop("password")
    assert client.post("/register", json=user_data).status_code == 422
    response = client.post("/register", json={**user_data, "password": {"value": "secret-value"}})
    assert response.status_code == 422
    assert "secret-value" not in response.text


def test_short_password_is_not_echoed(client, user_data):
    response = client.post("/register", json={**user_data, "password": "Xy7!"})
    assert response.status_code == 422
    assert "Xy7!" not in response.text


@pytest.mark.parametrize("login", ["STARTER_USER", "STARTER@EXAMPLE.COM"])
def test_login_by_username_or_email(client, registered_user, user_data, login):
    response = client.post("/token", data={"username": login, "password": user_data["password"]})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    token = response.json()["access_token"]
    profile = client.get("/users/me/", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json() == registered_user


@pytest.mark.parametrize(
    "username,password",
    [("starter_user", "wrong"), ("unknown", "safe-password-123"), ("starter_user", "a" * 73)],
)
def test_invalid_login(client, registered_user, username, password):
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_disabled_user_cannot_login_or_use_existing_token(client, db, token, user_data):
    user = db.scalar(select(UserInDB))
    user.disabled = True
    db.commit()
    response = client.post(
        "/token", data={"username": user_data["username"], "password": user_data["password"]}
    )
    assert response.status_code == 401
    assert client.get("/users/me/", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_deleted_user_token_is_rejected(client, db, token):
    db.delete(db.scalar(select(UserInDB)))
    db.commit()
    assert client.get("/users/me/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_deleted_identity_is_not_reused(client, db, token, registered_user, user_data):
    db.delete(db.scalar(select(UserInDB)))
    db.commit()
    replacement = client.post("/register", json=user_data)
    assert replacement.status_code == 201
    assert replacement.json()["id"] != registered_user["id"]
    assert client.get("/users/me/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_missing_and_invalid_tokens(client):
    assert client.get("/users/me/").status_code == 401
    for token in ("garbage", create_access_token("1", timedelta(seconds=-1))):
        assert (
            client.get("/users/me/", headers={"Authorization": f"Bearer {token}"}).status_code
            == 401
        )


@pytest.mark.parametrize(
    "payload", [{"sub": "1"}, {"exp": 9999999999}, {"sub": []}, {"sub": "x"}, {"sub": "9" * 100}]
)
def test_signed_tokens_require_valid_subject_and_expiry(client, payload):
    settings = get_settings()
    if "exp" not in payload and payload != {"sub": "1"}:
        payload["exp"] = 9999999999
    token = jwt.encode(
        payload, settings.secret_key.get_secret_value(), algorithm=settings.algorithm
    )
    assert client.get("/users/me/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_duplicate_database_constraint_rolls_back_session(db, client, registered_user, user_data):
    # Bypass the precheck to exercise the database constraint used for racing requests.
    with pytest.raises(UserAlreadyExistsError):
        register_user_in_db(db, UserCreate(**user_data))
    assert db.scalar(select(UserInDB)).username == user_data["username"]
