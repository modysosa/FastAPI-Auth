from sqlalchemy import Boolean, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserInDB(Base):
    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
