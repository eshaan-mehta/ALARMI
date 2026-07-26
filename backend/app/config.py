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

    # How long the stubbed IFC extractor pretends to work before a design flips
    # to COMPLETE. Real value locally so the polling UI is exercised; tests set
    # it to 0 (see tests/conftest.py). The real processor removes the delay.
    processing_delay_seconds: float = 5.0

    # Azure Blob (deploy only). Empty locally → FakeBlobStore is used, so no
    # Azure account is needed for local dev or tests. Set in Azure via env; the
    # connection string is injected from a Container App secret.
    azure_storage_connection_string: str = ""
    blob_container: str = "alarmi"

    # Explicit browser origins allowed to call the API (used for real deploys —
    # set via env in Azure).
    cors_origins: list[str] = []

    # Dev convenience: allow the Vite server on any local port (5173, 5174, …)
    # over either localhost or 127.0.0.1, so a shifted port doesn't break CORS.
    cors_origin_regex: str = r"http://(localhost|127\.0\.0\.1):\d+"


settings = Settings()
