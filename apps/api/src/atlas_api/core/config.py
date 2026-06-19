from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Atlas"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    postgres_db: str = "atlas"
    postgres_user: str = "atlas"
    postgres_password: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    vector_dimensions: int = 1536
    ai_provider: str = "local"
    upload_dir: str = "data/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
