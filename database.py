"""Compatibility exports; new modules should import app.database directly."""

from app.database import Base as Base
from app.database import SessionLocal as SessionLocal
from app.database import engine as engine
