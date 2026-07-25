"""Unit tests for `app/designs/repository.py`."""

from datetime import datetime

from sqlalchemy import select

from app.designs import repository as repo
from app.designs.models import Design
from app.modules.models import Module
from app.projects import repository as projects_repo
from conftest import DESIGN_FIELDS, STATUSES


def _project(db, name="P", location="Waterloo, ON") -> str:
    return projects_repo.create_project(db, name, location).projectId


class TestCreateDesign:
    def test_returns_the_full_client_shape(self, db):
        out = repo.create_design(db, _project(db), "Ward A", "ward-a.ifc", 1024)
        assert set(out.model_dump()) == DESIGN_FIELDS

    def test_records_the_upload_facts(self, db):
        project_id = _project(db)
        out = repo.create_design(db, project_id, "Ward A", "ward-a.ifc", 4096)
        assert out.projectId == project_id
        assert out.name == "Ward A"
        assert out.fileName == "ward-a.ifc"
        assert out.fileSize == 4096
        assert out.designId.startswith("dsn_")
        assert datetime.fromisoformat(out.uploadTime).tzinfo is not None

    def test_status_is_one_the_client_renders(self, db):
        out = repo.create_design(db, _project(db), "A", "a.ifc", 10)
        assert out.status in STATUSES

    def test_returns_none_when_the_project_is_unknown(self, db):
        assert repo.create_design(db, "prj_missing", "A", "a.ifc", 10) is None

    def test_does_not_leave_a_partial_design_behind_on_a_bad_project(self, db):
        repo.create_design(db, "prj_missing", "A", "a.ifc", 10)
        assert db.scalar(select(Design)) is None

    def test_runs_the_processor_so_modules_exist(self, db):
        """FS5: the metadata has to be extracted and stored, not just the file
        recorded."""
        out = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        modules = db.scalars(
            select(Module).where(Module.design_id == out.designId)
        ).all()
        assert len(modules) >= 1

    def test_module_count_matches_the_stored_modules(self, db):
        out = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        stored = db.scalars(select(Module).where(Module.design_id == out.designId)).all()
        assert out.moduleCount == len(stored)


class TestListDesigns:
    def test_unknown_project_returns_nothing(self, db):
        assert repo.list_designs(db, "prj_missing") == []

    def test_scoped_to_one_project(self, db):
        a, b = _project(db, "A"), _project(db, "B")
        repo.create_design(db, a, "A design", "a.ifc", 10)
        repo.create_design(db, b, "B design", "b.ifc", 10)
        names = [d.name for d in repo.list_designs(db, a)]
        assert names == ["A design"]

    def test_returns_newest_first(self, db):
        project_id = _project(db)
        first = repo.create_design(db, project_id, "First", "1.ifc", 10)
        second = repo.create_design(db, project_id, "Second", "2.ifc", 11)
        ids = [d.designId for d in repo.list_designs(db, project_id)]
        assert ids == [second.designId, first.designId]

    def test_ships_metadata_only(self, db):
        """Load strategy is lazy: the list carries a count, never the modules
        themselves (they come from GET /designs/{id}/modules)."""
        project_id = _project(db)
        repo.create_design(db, project_id, "A", "a.ifc", 1024)
        assert "modules" not in repo.list_designs(db, project_id)[0].model_dump()


class TestGetDesign:
    def test_returns_the_design(self, db):
        created = repo.create_design(db, _project(db), "A", "a.ifc", 10)
        assert repo.get_design(db, created.designId).designId == created.designId

    def test_returns_none_when_unknown(self, db):
        assert repo.get_design(db, "dsn_missing") is None


class TestGetStatus:
    def test_returns_the_stored_status(self, db):
        created = repo.create_design(db, _project(db), "A", "a.ifc", 10)
        assert repo.get_status(db, created.designId) == created.status

    def test_returns_none_when_unknown(self, db):
        assert repo.get_status(db, "dsn_missing") is None


class TestListModules:
    def test_returns_none_when_the_design_is_unknown(self, db):
        """`None` is how the repository says 404 without knowing about HTTP."""
        assert repo.list_modules(db, "dsn_missing") is None

    def test_returns_the_designs_modules(self, db):
        created = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        assert len(repo.list_modules(db, created.designId)) == created.moduleCount

    def test_empty_while_still_processing(self, db):
        """Metadata is only meaningful once extraction finishes."""
        created = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        design = db.get(Design, created.designId)
        design.status = "PROCESSING"
        db.commit()
        assert repo.list_modules(db, created.designId) == []

    def test_scoped_to_one_design(self, db):
        project_id = _project(db)
        one = repo.create_design(db, project_id, "One", "1.ifc", 1024)
        two = repo.create_design(db, project_id, "Two", "2.ifc", 2048)
        ids_one = {m.moduleId for m in repo.list_modules(db, one.designId)}
        ids_two = {m.moduleId for m in repo.list_modules(db, two.designId)}
        assert ids_one.isdisjoint(ids_two)

    def test_order_is_stable_across_calls(self, db):
        created = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        first = [m.moduleId for m in repo.list_modules(db, created.designId)]
        second = [m.moduleId for m in repo.list_modules(db, created.designId)]
        assert first == second


class TestUpdateDesign:
    def test_renames(self, db):
        created = repo.create_design(db, _project(db), "Old", "a.ifc", 10)
        assert repo.update_design(db, created.designId, {"name": "New"}).name == "New"

    def test_returns_none_when_unknown(self, db):
        assert repo.update_design(db, "dsn_missing", {"name": "New"}) is None

    def test_ignores_fields_that_are_not_user_editable(self, db):
        """FS3 allows rename only — the upload facts and the processing status
        are the server's to set."""
        created = repo.create_design(db, _project(db), "Old", "a.ifc", 10)
        updated = repo.update_design(
            db,
            created.designId,
            {"name": "New", "status": "ERROR", "fileName": "hacked.ifc", "fileSize": 9},
        )
        assert updated.status == created.status
        assert updated.fileName == "a.ifc"
        assert updated.fileSize == 10

    def test_empty_patch_changes_nothing(self, db):
        created = repo.create_design(db, _project(db), "Old", "a.ifc", 10)
        assert repo.update_design(db, created.designId, {}).name == "Old"


class TestDeleteDesign:
    def test_returns_true_and_removes_the_row(self, db):
        created = repo.create_design(db, _project(db), "A", "a.ifc", 10)
        assert repo.delete_design(db, created.designId) is True
        assert db.get(Design, created.designId) is None

    def test_returns_false_when_unknown(self, db):
        assert repo.delete_design(db, "dsn_missing") is False

    def test_cascades_to_the_designs_modules(self, db):
        """No orphaned metadata — the modules only exist because of this file."""
        created = repo.create_design(db, _project(db), "A", "a.ifc", 1024)
        repo.delete_design(db, created.designId)
        assert (
            db.scalar(select(Module).where(Module.design_id == created.designId)) is None
        )

    def test_leaves_other_designs_alone(self, db):
        project_id = _project(db)
        keep = repo.create_design(db, project_id, "Keep", "k.ifc", 1024)
        drop = repo.create_design(db, project_id, "Drop", "d.ifc", 2048)
        repo.delete_design(db, drop.designId)
        assert repo.get_design(db, keep.designId) is not None
        assert len(repo.list_modules(db, keep.designId)) == keep.moduleCount

    def test_drops_the_projects_design_count(self, db):
        project_id = _project(db)
        created = repo.create_design(db, project_id, "A", "a.ifc", 10)
        repo.delete_design(db, created.designId)
        counts = {p.projectId: p.designCount for p in projects_repo.list_projects(db)}
        assert counts[project_id] == 0
