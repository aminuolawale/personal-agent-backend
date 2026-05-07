from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    migration_database_url: str | None = Field(None, alias="MIGRATION_DATABASE_URL")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")
    environment: str = Field("development", alias="ENVIRONMENT")

    @property
    def sqlalchemy_database_url(self) -> str:
        return self._normalize_postgres_url(self.database_url)

    @property
    def sqlalchemy_migration_database_url(self) -> str:
        return self._normalize_postgres_url(self.migration_database_url or self.database_url)

    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        if url.startswith("postgres://"):
            url = "postgresql://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
