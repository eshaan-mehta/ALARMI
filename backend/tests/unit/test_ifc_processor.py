"""Unit tests for `app/ifc/processor.py` — the extraction SEAM.

Phase 1 ships a stub, but the *interface* it presents is already spec: given a
reference to an uploaded IFC it returns one dict per module carrying the metadata
the design doc's Table 5 lists (type, dimensions, room id, unit scale). These
tests pin that interface so swapping in the real IfcOpenShell extractor is a
drop-in change. Attaching those modules to a design and moving it to a terminal
status is the worker's job (see tests/unit/test_processing_worker.py).
"""

import pytest

from app.ifc.processor import _generate_modules, extract
from conftest import UNIT_SCALES


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


class TestExtract:
    """`extract` is what the worker calls off the request. It returns metadata
    dicts only — it never touches the database. (The 0-second sleep in tests
    comes from PROCESSING_DELAY_SECONDS=0 in conftest.)"""

    def test_returns_the_modules_for_the_file(self):
        modules = extract("designs/dsn_1/source.ifc", 1024)
        assert modules == _generate_modules(1024)

    def test_yields_at_least_one_module(self):
        assert len(extract("designs/dsn_1/source.ifc", 1)) >= 1

    def test_modules_carry_the_table_5_metadata(self):
        for module in extract("designs/dsn_1/source.ifc", 4096):
            assert module["type"]
            assert module["room_id"]
            assert module["unit_scale"] in UNIT_SCALES
            assert set(module["dimensions"]) == {"x", "y", "z"}
            assert all(v > 0 for v in module["dimensions"].values())
