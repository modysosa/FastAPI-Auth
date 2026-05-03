from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user_model import UserInDB
from app.utils.security import verify_password


def get_user_by_login(db: Session, login: str) -> UserInDB | None:
    query = text(
        """
        SELECT id, name, email, password, admin
        FROM users
        WHERE name = :login OR email = :login
        LIMIT 1
        """
    )
    row = db.execute(query, {"login": login}).mappings().first()
    if not row:
        return None

    return UserInDB(
        username=row["name"],
        email=row["email"],
        hashed_password=row["password"],
        admin=row["admin"],
        disabled=False,
    )


def get_user_by_username(db: Session, username: str) -> UserInDB | None:
    query = text(
        """
        SELECT id, name, email, password, admin
        FROM users
        WHERE name = :username
        LIMIT 1
        """
    )
    row = db.execute(query, {"username": username}).mappings().first()
    if not row:
        return None

    return UserInDB(
        username=row["name"],
        email=row["email"],
        hashed_password=row["password"],
        admin=row["admin"],
        disabled=False,
    )


def authenticate_user(db: Session, login: str, password: str):
    user = get_user_by_login(db, login)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def register_user_in_db(db: Session, username: str, email: str, password: str) -> None:
    query = text(
        """
        INSERT INTO users (name, email, password)
        VALUES (:name, :email, :password)
        """
    )
    db.execute(query, {"name": username, "email": email, "password": password})
    db.commit()