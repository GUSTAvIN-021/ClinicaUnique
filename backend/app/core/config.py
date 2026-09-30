from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=False, extra="ignore")
    app_env: str = "development"
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    seed_admin_email: str = "admin@unique.local"
    seed_admin_password: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
