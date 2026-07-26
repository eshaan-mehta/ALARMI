"""Unit tests for the async processing worker (`app/processing/worker.py`).

The worker is the scaffolding the IFC-processing team plugs into: it runs off
the request (enqueued as a background task), calls the stubbed extractor,
persists the extracted modules, publishes a GLB per module, and moves the design
into a terminal status. It owns its own DB session because the request that
enqueued it is already gone by the time it runs.
"""

from sqlalchemy import select

from app import blob
from app.designs.models import Design
from app.modules.models import Module
from app.processing import worker
from app.projects.models import Project
from conftest import UNIT_SCALES


def _stored_processing_design(db, design_id="dsn_1") -> str:
    """A design sitting in PROCESSING, the state the worker picks up."""
    db.add(
        Project(
            project_id="prj_1", name="P", location="X",
            created_time="2026-01-01T00:00:00+00:00",
        )
    )
    db.add(
        Design(
            design_id=design_id, project_id="prj_1", name="D", file_name="d.ifc",
            file_size=1024, status="PROCESSING", upload_time="2026-01-01T00:00:00+00:00",
        )
    )
    db.commit()
    return design_id


def _boom(*_args, **_kwargs):
    raise RuntimeError("bad ifc")


class TestSuccessfulRun:
    def test_moves_the_design_to_complete(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert db.get(Design, "dsn_1").status == "COMPLETE"

    def test_records_a_processed_timestamp(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert db.get(Design, "dsn_1").processed_time

    def test_clears_any_error(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert db.get(Design, "dsn_1").error is None

    def test_attaches_at_least_one_module(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        rows = db.scalars(select(Module).where(Module.design_id == "dsn_1")).all()
        assert len(rows) >= 1

    def test_modules_carry_table_5_metadata(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        for m in db.scalars(select(Module).where(Module.design_id == "dsn_1")).all():
            assert m.type and m.room_id
            assert m.unit_scale in UNIT_SCALES
            assert set(m.dimensions) == {"x", "y", "z"}
            assert all(v > 0 for v in m.dimensions.values())

    def test_module_ids_are_unique_and_prefixed(self, db):
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        ids = [m.module_id for m in db.scalars(select(Module).where(Module.design_id == "dsn_1")).all()]
        assert len(ids) == len(set(ids))
        assert all(i.startswith("mod_") for i in ids)

    def test_publishes_a_glb_for_every_module(self, db, monkeypatch):
        """The AR viewer downloads each module's GLB — the worker must publish
        one per module under its id, so the object URL endpoint can point at it."""
        put_keys: list[str] = []
        monkeypatch.setattr(blob.get_blob_store(), "put", lambda key, data: put_keys.append(key))
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        ids = [m.module_id for m in db.scalars(select(Module).where(Module.design_id == "dsn_1")).all()]
        for module_id in ids:
            assert blob.glb_key(module_id) in put_keys


class TestFailedRun:
    def test_marks_the_design_error_when_extraction_raises(self, db, monkeypatch):
        monkeypatch.setattr(worker.processor, "extract", _boom)
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert db.get(Design, "dsn_1").status == "ERROR"

    def test_stores_the_error_message(self, db, monkeypatch):
        monkeypatch.setattr(worker.processor, "extract", _boom)
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert "bad ifc" in (db.get(Design, "dsn_1").error or "")

    def test_leaves_no_modules_when_extraction_fails(self, db, monkeypatch):
        """A failed parse must not leave half-written metadata behind."""
        monkeypatch.setattr(worker.processor, "extract", _boom)
        _stored_processing_design(db)
        worker.run_job("dsn_1")
        db.expire_all()
        assert db.scalars(select(Module).where(Module.design_id == "dsn_1")).all() == []


class TestMissingDesign:
    def test_unknown_design_is_a_safe_noop(self, db):
        """The design can be deleted between enqueue and run — the worker must
        not raise on a job for a design that no longer exists."""
        worker.run_job("dsn_missing")  # must not raise
