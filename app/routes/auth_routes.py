from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.middlewares.auth_middleware import get_current_active_user, get_db
from app.schemas.user_schema import Token, User
from app.services.auth_service import (
    authenticate_user,
    get_user_by_login,
    register_user_in_db,
)
from app.utils.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, hash_password

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=User)
async def register_user(user: User, db: Session = Depends(get_db)):
    existing_user = get_user_by_login(db, user.username) or get_user_by_login(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = hash_password(user.password)
    register_user_in_db(db, user.username, user.email, hashed_password)
    return user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]