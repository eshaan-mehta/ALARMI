# ALARMI — Backend

REST API for ALARMI. **Phase 1:** the web-app contract served by FastAPI over
SQLite. No Azure, no Docker, no real IFC processing yet — those land in later
slices.

Built on **FastAPI** + **SQLAlchemy 2** (SQLite) + **Pydantic**, managed with **uv**.
Python because the future IFC processor (IfcOpenShell) is Python-only, so one
language covers the whole backend.

## Layout

Organized **by domain** — each resource folder mirrors the frontend's
`data/<domain>/`, so a feature lives in one place instead of scattered across
type-based files.

```
cli.py              # dev CLI entry points (uv run dev / uv run seed)
app/
  main.py           # FastAPI app: CORS, {message} error handler, mounts routers, startup
  config.py         # env settings — DATABASE_URL is the local↔Azure swap point
  db.py             # SQLAlchemy engine + session-per-request + create_all
  errors.py         # ApiError
  util.py           # id + timestamp helpers
  seed.py           # optional demo data
  ifc/
    processor.py    # IFC processor — STUB (fabricates placeholder modules)
  projects/         # router · repository · schemas · models
  designs/          #   "
  modules/          #   "
```

Each domain folder holds the same four pieces (the backend analog of the
frontend's `api`/`hooks`/`types`):

| File | Role |
|------|------|
| `router.py` | HTTP endpoints + validation + status codes |
| `repository.py` | DB queries and mutations |
| `schemas.py` | Pydantic request/response shapes (camelCase, match the frontend) |
| `models.py` | the ORM table |

**Data model:** a **Project** holds many **Designs** (one uploaded IFC each); a
completed Design holds many **Modules** (the extracted components + their
metadata). Identity is always the id, never the name.

**Request flow:** router (validate, HTTP status) → repository (query/mutate) →
model (SQLite). Errors come back as `{ "message": ... }`.

## Running

```bash
cd backend
uv run dev                  # server on :8000 (--reload); keeps existing data
uv run dev --seed           # seed demo data first, then run
uv run dev --reset --seed   # wipe the DB, re-seed, then run (clean slate)
uv run dev --port 8001      # different port

uv run seed                 # just (re)seed, don't start the server
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

## Endpoints

```
GET    /api/projects/all_projects
POST   /api/projects                        { name, location }
PATCH  /api/projects/{projectId}            { new_name }
GET    /api/projects/{projectId}/designs
POST   /api/projects/{projectId}/designs    multipart { name, file }
GET    /api/designs/{designId}
PATCH  /api/designs/{designId}              { name }
DELETE /api/designs/{designId}
GET    /api/designs/{designId}/status
GET    /api/designs/{designId}/modules
PATCH  /api/modules/{moduleId}              { type?, dimensions?, roomId?, unitScale? }
GET    /api/health
```

## Deferred (later slices)

Real IFC processing (IfcOpenShell) · Azure Blob + Azure SQL · async queue ·
Alembic migrations · auth · the mobile/object endpoints (`/objects/get_url`,
`/modules/project_modules`) · deployment + IaC.
