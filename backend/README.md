# ALARMI — Backend

Built on **FastAPI** + **SQLAlchemy 2** (SQLite) + **Pydantic**, managed with **uv**.

## Layout

Each domain folder holds the same four pieces (the backend analog of the
frontend's `api`/`hooks`/`types`):

| File | Role |
|------|------|
| `router.py` | HTTP endpoints + validation + status codes |
| `repository.py` | DB queries and mutations |
| `schemas.py` | Pydantic request/response shapes |
| `models.py` | the ORM table |

**Data model:** a **Project** holds many **Designs** (one uploaded IFC each); a
completed Design holds many **Modules** (the extracted components + their
metadata). 

## Running

```bash
cd backend
uv run dev                  # server on :8000 (--reload); keeps existing data
uv run dev --seed           # seed demo data first, then run
uv run dev --reset --seed   # wipe the DB, re-seed, then run (clean slate)
```

- API at `http://localhost:8000/api` · interactive docs at `http://localhost:8000/docs`.
- Data lives in `backend/alarmi.db` and **persists on disk** across restarts.
  Delete it (or use `--reset`) to start fresh.
- First run auto-creates `.venv` from `uv.lock`; no manual activation needed.

## Configuration

| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:///./alarmi.db` | Metadata store. Set to the Azure SQL connection string when deployed |
| `APP_ENV` | `local` | `local` \| `azure` (informational) |

No `.env` needed for local dev — copy `.env.example` only to override.


