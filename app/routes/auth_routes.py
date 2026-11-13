from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.middlewares.auth_middleware import get_current_active_user
from app.models.user_model import UserInDB
from app.schemas.user_schema import Token, UserCreate, UserRead
from app.services.auth_service import (
    UserAlreadyExistsError,
    authenticate_user,
    get_user_by_login,
    register_user_in_db,
)
from app.utils.security import create_access_token

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_login(db, user.username) or get_user_by_login(db, str(user.email)):
        raise HTTPException(status_code=409, detail="Username or email already registered")
    try:
        return register_user_in_db(db, user)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=409, detail="Username or email already registered"
        ) from None


@router.post("/token", response_model=Token)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user or user.disabled:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/users/me/", response_model=UserRead)
def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user
