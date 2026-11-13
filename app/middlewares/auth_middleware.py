import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models.user_model import UserInDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
            raise credentials_exception
        if len(subject) > 19 or int(subject) < 1 or int(subject) > 2**63 - 1:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception from None
    user = db.get(UserInDB, int(subject))
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user
