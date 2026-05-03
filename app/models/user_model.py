from pydantic import BaseModel


class UserInDB(BaseModel):
    username: str
    email: str | None = None
    hashed_password: str
    admin: bool | None = None
    disabled: bool = False