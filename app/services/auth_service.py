from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_model import UserInDB
from app.schemas.user_schema import UserCreate
from app.utils.security import hash_password, verify_password

DUMMY_HASH = hash_password("unused-dummy-password")


class UserAlreadyExistsError(Exception):
    pass


def get_user_by_login(db: Session, login: str) -> UserInDB | None:
    login = login.strip().lower()
    return db.scalar(
        select(UserInDB).where(or_(UserInDB.username == login, UserInDB.email == login))
    )


def authenticate_user(db: Session, login: str, password: str) -> UserInDB | None:
    user = get_user_by_login(db, login)
    valid = verify_password(password, user.hashed_password if user else DUMMY_HASH)
    return user if user and valid else None


def register_user_in_db(db: Session, data: UserCreate) -> UserInDB:
    user = UserInDB(
        username=data.username,
        email=str(data.email),
        hashed_password=hash_password(data.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExistsError from exc
    db.refresh(user)
    return user
