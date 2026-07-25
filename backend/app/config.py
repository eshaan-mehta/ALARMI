from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, read from the environment (with a .env fallback).

    This is the single place local vs. deployed differ: locally DATABASE_URL is
    a SQLite file; in Azure it's the Azure SQL connection string. The code that
    reads it is identical.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./alarmi.db"
    app_env: str = "local"

    # Explicit browser origins allowed to call the API (used for real deploys —
    # set via env in Azure).
    cors_origins: list[str] = []

    # Dev convenience: allow the Vite server on any local port (5173, 5174, …)
    # over either localhost or 127.0.0.1, so a shifted port doesn't break CORS.
    cors_origin_regex: str = r"http://(localhost|127\.0\.0\.1):\d+"


settings = Settings()
