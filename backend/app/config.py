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

    # Origins allowed to call the API from a browser (the Vite dev server).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
