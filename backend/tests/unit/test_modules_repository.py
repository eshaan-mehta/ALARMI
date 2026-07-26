"""Unit tests for `app/modules/repository.py`.

Per-module metadata editing is a deliberate extension of the design doc (which
only lists view/rename/delete for files) and is justified by Table 6 storing the
metadata per module. Editing must be a genuine partial update: the panel only
ever sends the fields the user touched.
"""

from app.designs import repository as designs_repo
from app.modules import repository as repo
from app.modules.models import Module
from app.processing.worker import run_job
from app.projects import repository as projects_repo
from conftest import MODULE_FIELDS


def _module(db) -> str:
    """A module belonging to a fully-processed design. Extraction is async now,
    so we run the worker (delay 0 in tests) to produce the modules an upload
    used to create synchronously."""
    project_id = projects_repo.create_project(db, "P", "Waterloo, ON").projectId
    design = designs_repo.create_design(db, project_id, "D", "d.ifc", 1024)
    run_job(design.designId)
    db.expire_all()
    return designs_repo.list_modules(db, design.designId)[0].moduleId


class TestListForDesign:
    def test_returns_the_client_shape(self, db):
        module_id = _module(db)
        design_id = db.get(Module, module_id).design_id
        out = repo.list_for_design(db, design_id)
        assert set(out[0].model_dump()) == MODULE_FIELDS

    def test_unknown_design_returns_an_empty_list(self, db):
        assert repo.list_for_design(db, "dsn_missing") == []


class TestUpdateModule:
    def test_returns_none_when_unknown(self, db):
        assert repo.update_module(db, "mod_missing", {"type": "Wall Panel"}) is None

    def test_updates_a_single_field(self, db):
        module_id = _module(db)
        assert repo.update_module(db, module_id, {"type": "Wall Panel"}).type == "Wall Panel"

    def test_leaves_untouched_fields_alone(self, db):
        module_id = _module(db)
        before = repo.to_module_out(db.get(Module, module_id))
        after = repo.update_module(db, module_id, {"type": "Wall Panel"})
        assert after.dimensions == before.dimensions
        assert after.roomId == before.roomId
        assert after.unitScale == before.unitScale

    def test_updates_dimensions(self, db):
        module_id = _module(db)
        out = repo.update_module(
            db, module_id, {"dimensions": {"x": 3.6, "y": 1.4, "z": 0.2}}
        )
        assert out.dimensions.model_dump() == {"x": 3.6, "y": 1.4, "z": 0.2}

    def test_updates_room_and_unit_scale(self, db):
        module_id = _module(db)
        out = repo.update_module(
            db, module_id, {"roomId": "IfcSpace_WardA_Bed01", "unitScale": "CENTIMETRE"}
        )
        assert out.roomId == "IfcSpace_WardA_Bed01"
        assert out.unitScale == "CENTIMETRE"

    def test_persists(self, db):
        module_id = _module(db)
        repo.update_module(db, module_id, {"type": "Utility Panel"})
        assert db.get(Module, module_id).type == "Utility Panel"

    def test_empty_patch_is_a_no_op(self, db):
        module_id = _module(db)
        before = repo.to_module_out(db.get(Module, module_id))
        assert repo.update_module(db, module_id, {}) == before

    def test_does_not_move_the_module_between_designs(self, db):
        """A metadata edit can't re-parent a module."""
        module_id = _module(db)
        design_id = db.get(Module, module_id).design_id
        repo.update_module(db, module_id, {"designId": "dsn_elsewhere", "moduleId": "mod_x"})
        row = db.get(Module, module_id)
        assert row is not None
        assert row.design_id == design_id


class TestToModuleOut:
    def test_maps_columns_to_the_client_camel_case(self, db):
        module_id = _module(db)
        row = db.get(Module, module_id)
        row.type = "Hospital Headwall"
        row.dimensions = {"x": 3.6, "y": 1.4, "z": 0.2}
        row.room_id = "IfcSpace_WardA_Bed01"
        row.unit_scale = "METRE"
        db.commit()
        assert repo.to_module_out(row).model_dump() == {
            "moduleId": module_id,
            "type": "Hospital Headwall",
            "dimensions": {"x": 3.6, "y": 1.4, "z": 0.2},
            "roomId": "IfcSpace_WardA_Bed01",
            "unitScale": "METRE",
        }
