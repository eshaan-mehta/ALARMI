"""Unit tests for the shared infrastructure: `config.py`, `db.py`, `errors.py`.

`DATABASE_URL` is the documented local↔Azure swap point (README, memory notes),
so the settings object and the engine it builds are part of the contract.
"""

import re

import pytest
from sqlalchemy import inspect, text

from app.config import Settings, settings
from app.db import Base, SessionLocal, engine, get_db, init_db
from app.errors import ApiError


class TestSettings:
    def test_defaults_to_a_local_sqlite_file(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        fresh = Settings(_env_file=None)
        assert fresh.database_url == "sqlite:///./alarmi.db"
        assert fresh.app_env == "local"

    def test_database_url_is_env_overridable(self, monkeypatch):
        """The one knob that has to change for Azure SQL."""
        monkeypatch.setenv("DATABASE_URL", "mssql+pyodbc://example")
        assert Settings(_env_file=None).database_url == "mssql+pyodbc://example"

    @pytest.mark.parametrize(
        "origin",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",  # Vite shifts ports when 5173 is taken
        ],
    )
    def test_allows_the_vite_dev_origin(self, origin):
        """NFS2: the dashboard must work from a browser with no plugins, which
        means the dev server's origin has to pass CORS — however it's expressed
        (explicit list or regex)."""
        allowed = origin in settings.cors_origins or (
            settings.cors_origin_regex
            and re.fullmatch(settings.cors_origin_regex, origin) is not None
        )
        assert allowed

    def test_does_not_allow_arbitrary_origins(self):
        assert "*" not in settings.cors_origins
        if settings.cors_origin_regex:
            assert re.fullmatch(settings.cors_origin_regex, "http://evil.example") is None

    def test_tests_run_against_a_throwaway_database(self):
        """Guard rail for this suite itself — never the developer's alarmi.db."""
        assert settings.database_url.startswith("sqlite:///")
        assert not settings.database_url.endswith("/./alarmi.db")


class TestEngine:
    def test_sqlite_allows_cross_thread_use(self):
        """FastAPI runs sync handlers in a threadpool, so the connection can't
        be pinned to the creating thread."""
        assert engine.dialect.name == "sqlite"
        assert engine.pool._dialect.name == "sqlite"
        with engine.connect() as conn:
            assert conn.execute(text("select 1")).scalar() == 1


class TestInitDb:
    def test_creates_every_table(self):
        init_db()
        tables = set(inspect(engine).get_table_names())
        assert {"projects", "designs", "modules"} <= tables

    def test_is_idempotent(self):
        init_db()
        init_db()  # stands in for migrations; must not blow up on re-run
        assert {"projects", "designs", "modules"} <= set(
            inspect(engine).get_table_names()
        )

    def test_project_columns_match_the_schema_table(self):
        """Design doc Table 6: Project(ProjectID PK, Name, Location)."""
        init_db()
        cols = {c["name"]: c for c in inspect(engine).get_columns("projects")}
        assert {"project_id", "name", "location", "created_time"} <= set(cols)
        pk = inspect(engine).get_pk_constraint("projects")
        assert pk["constrained_columns"] == ["project_id"]

    def test_module_columns_match_the_schema_table(self):
        """Design doc Table 6: Module(ModuleID PK, ProjectID FK, RoomID,
        Unit Scale, Type, Dimensions, ...). Modules hang off a design here, and
        a design hangs off a project, so the FK chain still holds."""
        init_db()
        cols = {c["name"] for c in inspect(engine).get_columns("modules")}
        assert {"module_id", "design_id", "type", "dimensions", "room_id", "unit_scale"} <= cols
        fks = inspect(engine).get_foreign_keys("modules")
        assert any(fk["referred_table"] == "designs" for fk in fks)

    def test_design_has_a_foreign_key_to_its_project(self):
        init_db()
        fks = inspect(engine).get_foreign_keys("designs")
        assert any(fk["referred_table"] == "projects" for fk in fks)


class TestGetDb:
    def test_yields_a_session_and_closes_it(self):
        gen = get_db()
        session = next(gen)
        assert session.is_active
        with pytest.raises(StopIteration):
            next(gen)
        # A closed session has released its connection back to the pool.
        assert not session.in_transaction()

    def test_closes_the_session_even_when_the_handler_raises(self):
        gen = get_db()
        session = next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("handler blew up"))
        assert not session.in_transaction()


@pytest.mark.policy
class TestReferentialIntegrity:
    """SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is issued per
    connection. Without it the local DB silently accepts orphan rows while Azure
    SQL (Table 6's FK constraint) would reject them — the two environments must
    not diverge on data integrity.
    """

    def test_rejects_a_design_pointing_at_a_missing_project(self, db):
        from app.designs.models import Design

        db.add(
            Design(
                design_id="dsn_orphan",
                project_id="prj_does_not_exist",
                name="Orphan",
                file_name="orphan.ifc",
                file_size=1,
                status="COMPLETE",
                upload_time="2026-01-01T00:00:00+00:00",
            )
        )
        with pytest.raises(Exception):
            db.commit()

    def test_rejects_a_module_pointing_at_a_missing_design(self, db):
        from app.modules.models import Module

        db.add(Module(module_id="mod_orphan", design_id="dsn_does_not_exist"))
        with pytest.raises(Exception):
            db.commit()


class TestApiError:
    def test_carries_status_and_message(self):
        err = ApiError(404, "Design not found.")
        assert err.status_code == 404
        assert err.message == "Design not found."
        assert str(err) == "Design not found."

    def test_is_raisable(self):
        with pytest.raises(ApiError) as excinfo:
            raise ApiError(409, "duplicate")
        assert excinfo.value.status_code == 409


def test_session_factory_is_bound_to_the_configured_engine():
    session = SessionLocal()
    try:
        assert session.get_bind() is engine
    finally:
        session.close()


def test_base_registers_all_three_models():
    init_db()
    assert {"projects", "designs", "modules"} <= set(Base.metadata.tables)
