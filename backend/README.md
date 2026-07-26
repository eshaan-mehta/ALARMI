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

## Processing pipeline

Upload does **not** block on IFC processing. `POST …/designs` stashes the file in
blob storage, returns immediately with `status=PROCESSING`, and enqueues a job;
a background worker extracts the modules and settles the design to `COMPLETE`
(or `ERROR`). The web client polls `GET …/status`; mobile follows
`GET /api/objects/get_url/{moduleId}` to a presigned GLB URL for AR.

Three seams keep this swappable:

| Module | Today (scaffolding) | Later |
|--------|--------------------|-------|
| `ifc/processor.py::extract` | sleeps, fabricates placeholder modules | **IFC team**: real IfcOpenShell extraction |
| `blob.py` | `FakeBlobStore` — accepts writes, drops bytes, returns a SAS-shaped URL | Azure Blob client |
| `processing/queue.py::enqueue` | in-process FastAPI background task | Azure Storage Queue + separate worker |

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
| `PROCESSING_DELAY_SECONDS` | `5` | How long the stub extractor pretends to work before a design flips to `COMPLETE`. Tests set it to `0` |

No `.env` needed for local dev — copy `.env.example` only to override.

## Tests

```bash
uv sync --group dev
uv run pytest                  # unit + endpoint + end-to-end
uv run pytest -m "not live"    # skip the tests that spawn a real uvicorn process
uv run pytest tests/spec -rxX  # spec surface not built yet (all xfail)
```

Tests are written against the design document and the web client's contract, so
a failure means the implementation disagrees with the spec — not that the test
needs adjusting. See [`tests/README.md`](tests/README.md) for where each rule
comes from and which open product decisions the suite takes a position on.

Everything runs against a throwaway SQLite file in a temp dir; `backend/alarmi.db`
is never touched.


