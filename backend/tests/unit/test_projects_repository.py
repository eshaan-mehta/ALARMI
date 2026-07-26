"""Unit tests for `app/projects/repository.py`.

The repository layer owns DB access and returns `None`/`[]`/`False` instead of
raising HTTP errors, so these tests cover the data behaviour; status codes are
covered in `tests/api/`.
"""

from datetime import datetime

import pytest

from app.designs.models import Design
from app.projects import repository as repo
from app.projects.models import Project
from conftest import PROJECT_FIELDS


def _add_design(db, project_id: str, design_id: str) -> None:
    db.add(
        Design(
            design_id=design_id,
            project_id=project_id,
            name=design_id,
            file_name=f"{design_id}.ifc",
            file_size=100,
            status="COMPLETE",
            upload_time="2026-01-01T00:00:00+00:00",
        )
    )
    db.commit()


class TestCreateProject:
    def test_returns_the_full_client_shape(self, db):
        out = repo.create_project(db, "Riverside Clinic", "Portland, OR")
        assert set(out.model_dump()) == PROJECT_FIELDS

    def test_assigns_a_prefixed_id_and_timestamp(self, db):
        out = repo.create_project(db, "Riverside Clinic", "Portland, OR")
        assert out.projectId.startswith("prj_")
        assert datetime.fromisoformat(out.createdTime).tzinfo is not None

    def test_starts_with_no_designs(self, db):
        assert repo.create_project(db, "A", "Waterloo, ON").designCount == 0

    def test_persists(self, db):
        out = repo.create_project(db, "A", "Waterloo, ON")
        assert db.get(Project, out.projectId) is not None

    def test_ids_are_unique_across_projects(self, db):
        a = repo.create_project(db, "A", "X")
        b = repo.create_project(db, "B", "Y")
        assert a.projectId != b.projectId


class TestListProjects:
    def test_empty_database_returns_an_empty_list(self, db):
        assert repo.list_projects(db) == []

    def test_returns_newest_first(self, db):
        """The dashboard shows the most recent work at the top."""
        first = repo.create_project(db, "First", "X")
        second = repo.create_project(db, "Second", "Y")
        ids = [p.projectId for p in repo.list_projects(db)]
        assert ids == [second.projectId, first.projectId]

    def test_design_count_reflects_stored_designs(self, db):
        project = repo.create_project(db, "A", "X")
        _add_design(db, project.projectId, "dsn_1")
        _add_design(db, project.projectId, "dsn_2")
        assert repo.list_projects(db)[0].designCount == 2

    def test_design_count_is_scoped_per_project(self, db):
        a = repo.create_project(db, "A", "X")
        b = repo.create_project(db, "B", "Y")
        _add_design(db, a.projectId, "dsn_a")
        counts = {p.projectId: p.designCount for p in repo.list_projects(db)}
        assert counts[a.projectId] == 1
        assert counts[b.projectId] == 0


class TestProjectNameExists:
    def test_false_when_absent(self, db):
        assert repo.project_name_exists(db, "Nope") is False

    def test_true_when_present(self, db):
        repo.create_project(db, "Riverside Clinic", "X")
        assert repo.project_name_exists(db, "Riverside Clinic") is True

    @pytest.mark.policy
    def test_ignores_case_and_surrounding_whitespace(self, db):
        """Names are the human handle for a project; "clinic" and "Clinic"
        sitting side by side in the dashboard is a bug, not a feature."""
        repo.create_project(db, "Riverside Clinic", "X")
        assert repo.project_name_exists(db, "riverside clinic") is True
        assert repo.project_name_exists(db, "  Riverside Clinic  ") is True


class TestRenameProject:
    def test_updates_the_name(self, db):
        project = repo.create_project(db, "Old", "X")
        renamed = repo.rename_project(db, project.projectId, "New")
        assert renamed.name == "New"

    def test_keeps_identity_and_metadata(self, db):
        """Identity is the id — a rename must not re-key anything or disturb
        the project's location, creation time, or children."""
        project = repo.create_project(db, "Old", "Portland, OR")
        _add_design(db, project.projectId, "dsn_1")
        renamed = repo.rename_project(db, project.projectId, "New")
        assert renamed.projectId == project.projectId
        assert renamed.location == project.location
        assert renamed.createdTime == project.createdTime
        assert renamed.designCount == 1

    def test_returns_none_for_an_unknown_id(self, db):
        assert repo.rename_project(db, "prj_missing", "New") is None

    def test_persists(self, db):
        project = repo.create_project(db, "Old", "X")
        repo.rename_project(db, project.projectId, "New")
        assert db.get(Project, project.projectId).name == "New"


class TestToProjectOut:
    def test_maps_snake_case_columns_to_the_client_camel_case(self, db):
        db.add(
            Project(
                project_id="prj_x",
                name="Riverside Clinic",
                location="Portland, OR",
                created_time="2026-01-01T00:00:00+00:00",
            )
        )
        db.commit()
        out = repo.to_project_out(db, db.get(Project, "prj_x"))
        assert out.model_dump() == {
            "projectId": "prj_x",
            "name": "Riverside Clinic",
            "location": "Portland, OR",
            "designCount": 0,
            "createdTime": "2026-01-01T00:00:00+00:00",
        }
