"""Shared fixtures for the ALARMI backend test suite.

``DATABASE_URL`` is set **before** the app is imported: ``app.config.settings``
is evaluated at import time and ``app.db.engine`` is built from it, so the env
var has to exist first. Every test therefore runs against a throwaway SQLite
file and never touches the developer's ``backend/alarmi.db``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="alarmi-tests-"))
_DB_PATH = _TMP_DIR / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["APP_ENV"] = "test"
# The stub extractor sleeps this long before a design flips to COMPLETE. Zero in
# tests so the enqueued job finishes instantly (the in-process TestClient runs it
# before the upload call even returns). This env also reaches the live-server
# subprocess via os.environ.
os.environ["PROCESSING_DELAY_SECONDS"] = "0"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.designs.models import Design  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Contract constants — the values the rest of the system agrees on.
# ---------------------------------------------------------------------------

#: Statuses the web client models (`website/src/data/designs/types.ts`).
STATUSES = {"PROCESSING", "COMPLETE", "ERROR"}

#: Unit scales the web client can display and convert
#: (`website/src/lib/units.ts::UNIT_SCALE_OPTIONS`).
UNIT_SCALES = {"METRE", "MILLIMETRE", "CENTIMETRE", "FOOT", "INCH"}

#: NFS12 — the web interface must support IFC uploads up to 1 GB.
ONE_GB = 1024**3

#: Fields of the `Project` the web client requires (projects/types.ts).
PROJECT_FIELDS = {"projectId", "name", "location", "designCount", "createdTime"}

#: Fields of the `Design` the web client requires (designs/types.ts).
DESIGN_FIELDS = {
    "designId",
    "projectId",
    "name",
    "fileName",
    "fileSize",
    "status",
    "uploadTime",
    "moduleCount",
}

#: Fields of the `Module` the web client requires (designs/types.ts).
MODULE_FIELDS = {"moduleId", "type", "dimensions", "roomId", "unitScale"}

_IFC_HEAD = (
    b"ISO-10303-21;\n"
    b"HEADER;\n"
    b"FILE_DESCRIPTION((''),'2;1');\n"
    b"FILE_NAME('test.ifc','2026-01-01T00:00:00',(''),(''),'','','');\n"
    b"FILE_SCHEMA(('IFC4'));\n"
    b"ENDSEC;\n"
    b"DATA;\n"
)
_IFC_TAIL = b"ENDSEC;\nEND-ISO-10303-21;\n"

MIN_IFC_SIZE = len(_IFC_HEAD) + len(_IFC_TAIL)


def ifc_bytes(size: int | None = None) -> bytes:
    """A syntactically plausible IFC payload, padded to exactly ``size`` bytes.

    Padding goes in a STEP comment so the file stays well-formed. ``size`` must
    be at least :data:`MIN_IFC_SIZE`.
    """
    if size is None:
        return _IFC_HEAD + _IFC_TAIL
    if size < MIN_IFC_SIZE:
        raise ValueError(f"size must be >= {MIN_IFC_SIZE}")
    pad = size - MIN_IFC_SIZE
    if pad == 0:
        return _IFC_HEAD + _IFC_TAIL
    if pad < 4:  # too small for a "/* */" comment — pad with newlines instead
        return _IFC_HEAD + b"\n" * pad + _IFC_TAIL
    return _IFC_HEAD + b"/*" + b"x" * (pad - 4) + b"*/" + _IFC_TAIL


# ---------------------------------------------------------------------------
# Database / app fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_db():
    """Every test starts from an empty schema."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(fresh_db) -> Session:
    """A session for the repository/unit tests (routers get their own)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(fresh_db) -> TestClient:
    """The real ASGI app, exercised end to end (lifespan included)."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def make_project(client):
    """Create a project through the API and return its JSON body."""

    def _make(name: str = "Riverside Clinic", location: str = "Portland, OR") -> dict:
        res = client.post("/api/projects", json={"name": name, "location": location})
        assert res.status_code == 201, res.text
        return res.json()

    return _make


@pytest.fixture
def upload_design(client):
    """Upload a design through the API and return the *settled* design.

    Upload now returns immediately with status PROCESSING; the extraction runs as
    a background job. Under the in-process TestClient that job finishes before the
    upload call returns, so a re-read reflects the COMPLETE design (with its
    modules) that the rest of the suite asserts against. ``size`` controls the
    payload length exactly, which drives the stub's fabricated module count.
    """

    def _upload(
        project_id: str,
        name: str = "Ward A Headwall",
        filename: str = "ward-a.ifc",
        size: int | None = None,
        content: bytes | None = None,
        expect: int = 201,
    ) -> dict:
        payload = content if content is not None else ifc_bytes(size)
        res = client.post(
            f"/api/projects/{project_id}/designs",
            data={"name": name},
            files={"file": (filename, payload, "application/octet-stream")},
        )
        assert res.status_code == expect, res.text
        if expect != 201:
            return res.json()
        return client.get(f"/api/designs/{res.json()['designId']}").json()

    return _upload


@pytest.fixture
def mark_processing():
    """Force a settled design back to PROCESSING.

    The in-process TestClient runs the background job before the upload call
    returns, so no design is ever *caught* mid-extraction — the only way to
    exercise the paths that care about an in-flight design is to put one there.
    """

    def _mark(design_id: str) -> None:
        with SessionLocal() as session:
            session.get(Design, design_id).status = "PROCESSING"
            session.commit()

    return _mark


@pytest.fixture
def project(make_project) -> dict:
    return make_project()


@pytest.fixture
def design(project, upload_design) -> dict:
    """A design whose stub processing fabricates the maximum 3 modules."""
    return upload_design(project["projectId"], size=MIN_IFC_SIZE + (2 - MIN_IFC_SIZE % 3) % 3)
