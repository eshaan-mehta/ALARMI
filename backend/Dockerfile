# ALARMI backend image — FastAPI on uvicorn, built for Azure Container Apps.
#
# Two things beyond a plain Python image:
#   1. Microsoft ODBC Driver 18 — pyodbc needs it to reach Azure SQL.
#   2. `uv sync --extra azure` — pulls pyodbc + azure-storage-blob (the deploy
#      extra); the default install stays SQLite + FakeBlobStore.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# --- Microsoft ODBC Driver 18 (for Azure SQL / pyodbc) ---
# The packages-microsoft-prod.deb registers MS's apt repo + signing key cleanly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev \
    && apt-get purge -y --auto-remove gnupg \
    && rm -rf /var/lib/apt/lists/*

# --- uv (fast, lockfile-driven installs) ---
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app

# Install deps first (cached until the lockfile changes). cli.py is copied
# because the project itself is built (hatchling ships cli.py for the entry
# points); --no-dev drops pytest/httpx, --extra azure adds the deploy deps.
COPY pyproject.toml uv.lock cli.py ./
RUN uv sync --frozen --no-dev --extra azure

# App code last so edits don't bust the dependency layer.
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
