"""Unit tests for `app/seed.py` and the dev CLI (`cli.py`).

Demo data is what a demo runs on, so it has to be internally consistent and safe
to re-run. The CLI is the documented way to start the backend (`uv run dev`), so
its flags are part of the developer-facing contract in the README.
"""

from datetime import datetime

import pytest
from sqlalchemy import select

import cli
from app.designs.models import Design
from app.modules.models import Module
from app.projects.models import Project
from app.seed import seed
from conftest import STATUSES, UNIT_SCALES


class TestSeed:
    def test_populates_all_three_tables(self, db):
        seed()
        assert db.scalars(select(Project)).all()
        assert db.scalars(select(Design)).all()
        assert db.scalars(select(Module)).all()

    def test_is_idempotent(self, db):
        """`uv run dev --seed` is documented as safe to re-run: it must not
        duplicate or crash on an already-populated DB."""
        seed()
        before = len(db.scalars(select(Design)).all())
        seed()
        db.expire_all()
        assert len(db.scalars(select(Design)).all()) == before

    def test_every_design_points_at_a_real_project(self, db):
        seed()
        project_ids = {p.project_id for p in db.scalars(select(Project)).all()}
        assert all(d.project_id in project_ids for d in db.scalars(select(Design)).all())

    def test_every_module_points_at_a_real_design(self, db):
        seed()
        design_ids = {d.design_id for d in db.scalars(select(Design)).all()}
        assert all(m.design_id in design_ids for m in db.scalars(select(Module)).all())

    def test_statuses_are_renderable(self, db):
        seed()
        assert {d.status for d in db.scalars(select(Design)).all()} <= STATUSES

    def test_unit_scales_are_convertible(self, db):
        seed()
        scales = {m.unit_scale for m in db.scalars(select(Module)).all()}
        assert scales <= UNIT_SCALES

    def test_dimensions_are_positive(self, db):
        seed()
        for module in db.scalars(select(Module)).all():
            assert set(module.dimensions) == {"x", "y", "z"}
            assert all(v > 0 for v in module.dimensions.values())

    def test_project_names_are_unique(self, db):
        seed()
        names = [p.name for p in db.scalars(select(Project)).all()]
        assert len(names) == len(set(names))

    def test_timestamps_are_iso_8601(self, db):
        seed()
        for project in db.scalars(select(Project)).all():
            assert datetime.fromisoformat(project.created_time).tzinfo is not None
        for design in db.scalars(select(Design)).all():
            assert datetime.fromisoformat(design.upload_time).tzinfo is not None

    def test_seeded_data_reads_back_through_the_api(self, client, db):
        """The seed exists to make the dashboard non-empty — prove it renders."""
        seed()
        projects = client.get("/api/projects/all_projects").json()
        assert projects
        total_designs = 0
        for project in projects:
            designs = client.get(f"/api/projects/{project['projectId']}/designs").json()
            assert len(designs) == project["designCount"]
            total_designs += len(designs)
            for design in designs:
                modules = client.get(f"/api/designs/{design['designId']}/modules").json()
                assert len(modules) == design["moduleCount"]
        assert total_designs > 0


class TestDevCli:
    """`dev` shells out to uvicorn; the tests replace the subprocess so nothing
    actually binds a port."""

    @pytest.fixture
    def calls(self, monkeypatch, tmp_path):
        recorded: list[list[str]] = []
        monkeypatch.setattr(cli, "_run", lambda cmd: recorded.append(cmd) or 0)
        monkeypatch.chdir(tmp_path)
        return recorded

    def _argv(self, monkeypatch, *args: str) -> None:
        monkeypatch.setattr("sys.argv", ["dev", *args])

    def test_starts_uvicorn_on_the_default_port(self, calls, monkeypatch):
        self._argv(monkeypatch)
        cli.dev()
        assert any("uvicorn" in c and "app.main:app" in c and "8000" in c for c in calls)

    def test_honours_the_port_flag(self, calls, monkeypatch):
        self._argv(monkeypatch, "--port", "8001")
        cli.dev()
        assert any("8001" in c for c in calls)

    def test_reload_is_on_for_local_development(self, calls, monkeypatch):
        self._argv(monkeypatch)
        cli.dev()
        assert any("--reload" in c for c in calls)

    def test_seed_flag_seeds_before_serving(self, calls, monkeypatch):
        self._argv(monkeypatch, "--seed")
        cli.dev()
        assert "app.seed" in calls[0]
        assert "uvicorn" in calls[-1]

    def test_no_seed_flag_means_no_seeding(self, calls, monkeypatch):
        self._argv(monkeypatch)
        cli.dev()
        assert not any("app.seed" in c for c in calls)

    def test_reset_deletes_the_local_database(self, calls, monkeypatch, tmp_path):
        (tmp_path / cli.DB).write_text("stale")
        self._argv(monkeypatch, "--reset")
        cli.dev()
        assert not (tmp_path / cli.DB).exists()

    def test_reset_is_fine_when_there_is_no_database(self, calls, monkeypatch):
        self._argv(monkeypatch, "--reset")
        cli.dev()  # must not raise

    def test_without_reset_the_database_survives(self, calls, monkeypatch, tmp_path):
        (tmp_path / cli.DB).write_text("keep me")
        self._argv(monkeypatch)
        cli.dev()
        assert (tmp_path / cli.DB).read_text() == "keep me"


class TestSeedCli:
    def test_exits_zero_on_success(self, monkeypatch):
        monkeypatch.setattr(cli, "_run", lambda cmd: 0)
        with pytest.raises(SystemExit) as excinfo:
            cli.seed()
        assert excinfo.value.code == 0

    def test_propagates_a_failure(self, monkeypatch):
        monkeypatch.setattr(cli, "_run", lambda cmd: 1)
        with pytest.raises(SystemExit) as excinfo:
            cli.seed()
        assert excinfo.value.code == 1

    def test_does_not_start_a_server(self, monkeypatch):
        recorded: list[list[str]] = []
        monkeypatch.setattr(cli, "_run", lambda cmd: recorded.append(cmd) or 0)
        with pytest.raises(SystemExit):
            cli.seed()
        assert not any("uvicorn" in c for c in recorded)
