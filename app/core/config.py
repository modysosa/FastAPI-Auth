from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    app_name: str = "FastAPI Auth Starter"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'dev.db').as_posix()}"
    secret_key: SecretStr
    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = []
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    login_rate_limit: int = Field(default=10, ge=1)
    register_rate_limit: int = Field(default=5, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_storage_uri: SecretStr = SecretStr("memory://")
    rate_limit_prefix: str = Field(default="fastapi-auth", min_length=1, max_length=100)

    @field_validator("rate_limit_storage_uri")
    @classmethod
    def validate_rate_limit_storage(cls, value: SecretStr) -> SecretStr:
        uri = value.get_secret_value()
        if uri != "memory://" and not uri.startswith(("redis://", "rediss://")):
            raise ValueError("Rate limit storage must use memory://, redis:// or rediss://")
        return value

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().strip()) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
