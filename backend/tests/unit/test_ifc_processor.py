"""Unit tests for `app/ifc/processor.py`.

Phase 1 ships a stub, but the *interface* it presents is already spec: given an
uploaded design it must attach modules carrying the metadata the design doc's
Table 5 lists (module type, dimensions, room id, unit scale) and move the design
into a terminal status (FS2, FS5). These tests pin that interface so swapping in
the real IfcOpenShell extractor is a drop-in change.
"""

import pytest
from sqlalchemy import select

from app.designs.models import Design
from app.ifc.processor import _generate_modules, process_design
from app.modules.models import Module
from app.projects.models import Project
from conftest import UNIT_SCALES


@pytest.fixture
def stored_design(db):
    project = Project(
        project_id="prj_test",
        name="Test",
        location="Waterloo, ON",
        created_time="2026-01-01T00:00:00+00:00",
    )
    design = Design(
        design_id="dsn_test",
        project_id="prj_test",
        name="Test design",
        file_name="test.ifc",
        file_size=1024,
        status="PROCESSING",
        upload_time="2026-01-01T00:00:00+00:00",
    )
    db.add_all([project, design])
    db.flush()
    return design


class TestGenerateModules:
    """An IFC file yields 1..N modules (doc §3.2.3: one per element flagged
    `FloorMark.IsMarkingModule`)."""

    @pytest.mark.parametrize("seed", [0, 1, 2, 41, 1024, 42_500_000])
    def test_yields_at_least_one_module(self, seed):
        assert len(_generate_modules(seed)) >= 1

    def test_is_deterministic_for_the_same_input(self):
        """The same file must always extract the same modules — re-processing
        an upload can't silently change the metadata."""
        assert _generate_modules(4242) == _generate_modules(4242)

    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 99, 1024])
    def test_every_module_carries_the_table_5_metadata(self, seed):
        for module in _generate_modules(seed):
            assert module["type"], "Table 5: Type (IfcElement subtype)"
            assert module["room_id"], "Table 5: RoomID (IfcSpace.GlobalId)"
            assert module["unit_scale"], "Table 5: Unit Scale (IfcProject.UnitsInContext)"
            assert set(module["dimensions"]) == {"x", "y", "z"}

    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 99, 1024])
    def test_dimensions_are_positive(self, seed):
        """Dimensions are physical extents; a zero or negative axis would break
        the AR overlay and the robot's footprint."""
        for module in _generate_modules(seed):
            dims = module["dimensions"]
            assert dims["x"] > 0 and dims["y"] > 0 and dims["z"] > 0

    @pytest.mark.parametrize("seed", [0, 1, 2, 7, 99, 1024])
    def test_unit_scale_is_one_the_client_understands(self, seed):
        """`website/src/lib/units.ts` can only convert/label these five."""
        for module in _generate_modules(seed):
            assert module["unit_scale"] in UNIT_SCALES

    def test_modules_from_one_file_share_a_unit_scale(self):
        """Unit scale comes from IfcProject.UnitsInContext — one per file."""
        for seed in (0, 1, 2, 55, 1024):
            scales = {m["unit_scale"] for m in _generate_modules(seed)}
            assert len(scales) == 1


class TestProcessDesign:
    def test_attaches_modules_to_the_design(self, db, stored_design):
        process_design(db, stored_design, stored_design.file_size)
        db.flush()
        rows = db.scalars(
            select(Module).where(Module.design_id == stored_design.design_id)
        ).all()
        assert len(rows) >= 1

    def test_moves_the_design_out_of_processing(self, db, stored_design):
        """FS2: a design must end up in a terminal, displayable state."""
        process_design(db, stored_design, stored_design.file_size)
        assert stored_design.status in {"COMPLETE", "ERROR"}

    def test_gives_every_module_a_unique_id(self, db, stored_design):
        process_design(db, stored_design, stored_design.file_size)
        db.flush()
        ids = [
            m.module_id
            for m in db.scalars(select(Module).where(Module.design_id == "dsn_test")).all()
        ]
        assert len(ids) == len(set(ids))
        assert all(i.startswith("mod_") for i in ids)

    def test_does_not_commit_the_transaction(self, db, stored_design):
        """The caller owns the transaction: a failure later in the upload must
        be able to roll the whole design back, modules included."""
        process_design(db, stored_design, stored_design.file_size)
        db.rollback()
        assert db.scalar(select(Module).where(Module.design_id == "dsn_test")) is None
        assert db.get(Design, "dsn_test") is None

    def test_two_designs_do_not_share_modules(self, db, stored_design):
        other = Design(
            design_id="dsn_other",
            project_id="prj_test",
            name="Other",
            file_name="other.ifc",
            file_size=2048,
            status="PROCESSING",
            upload_time="2026-01-01T00:00:00+00:00",
        )
        db.add(other)
        process_design(db, stored_design, stored_design.file_size)
        process_design(db, other, other.file_size)
        db.flush()
        mine = db.scalars(select(Module).where(Module.design_id == "dsn_test")).all()
        theirs = db.scalars(select(Module).where(Module.design_id == "dsn_other")).all()
        assert {m.module_id for m in mine}.isdisjoint({m.module_id for m in theirs})
