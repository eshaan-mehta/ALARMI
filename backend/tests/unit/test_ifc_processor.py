"""Unit tests for `app/ifc/processor.py` — IFC in, GLB + metadata out.

The processor opens the file for real now (IfcOpenShell → trimesh), so these run
against `tests/fixtures/SimpleWall.ifc`: one wall, one door, and the opening the
door sits in. Every renderable element is merged into a *single* module, so one
file yields one `ExtractedModule` carrying the design doc's Table 5 metadata and
the GLB bytes the AR viewer downloads.

Attaching those modules to a design and moving it to a terminal status is the
worker's job (see tests/unit/test_processing_worker.py).
"""

import pytest

from app.ifc.processor import _humanise, extract
from conftest import (
    SAMPLE_DIMENSIONS,
    SAMPLE_TYPE,
    UNIT_SCALES,
    empty_ifc_bytes,
    ifc_bytes,
)


@pytest.fixture(scope="module")
def modules():
    """Extraction is the slow part (real geometry), so do it once."""
    return extract(ifc_bytes())


class TestExtract:
    """`extract` is what the worker calls off the request. It takes the raw
    bytes of the upload and never touches the database."""

    def test_a_file_extracts_to_one_merged_module(self, modules):
        """Demo scope: the whole design is one module. The real pipeline splits
        on `FloorMark.IsMarkingModule`, which nothing writes yet."""
        assert len(modules) == 1

    def test_the_module_carries_the_table_5_metadata(self, modules):
        metadata = modules[0].metadata
        assert metadata["type"]
        assert metadata["room_id"]
        assert metadata["unit_scale"] in UNIT_SCALES
        assert set(metadata["dimensions"]) == {"x", "y", "z"}

    def test_the_metadata_keys_match_the_module_columns(self, modules):
        """The worker splats these into `Module(**metadata)`, so a renamed key
        is a TypeError at runtime rather than a test failure here."""
        from app.modules.models import Module

        assert set(modules[0].metadata) <= set(Module.__table__.columns.keys())

    def test_extraction_is_deterministic(self):
        """The same file must always extract the same metadata — re-processing
        an upload can't silently change what the user was shown."""
        assert extract(ifc_bytes())[0].metadata == extract(ifc_bytes())[0].metadata


class TestMetadataComesFromTheFile:
    """The values below are the sample's real geometry, not fabrications from
    the byte count (which is what the stub this replaced did)."""

    def test_dimensions_are_the_meshs_actual_extents(self, modules):
        assert modules[0].metadata["dimensions"] == SAMPLE_DIMENSIONS

    def test_dimensions_are_positive(self, modules):
        """Physical extents; a zero axis would break the AR overlay and the
        robot's footprint."""
        assert all(v > 0 for v in modules[0].metadata["dimensions"].values())

    def test_type_is_the_element_carrying_the_most_geometry(self, modules):
        """The sample is a wall with a door in it — the module is about the
        wall, so the door must not win the label."""
        assert modules[0].metadata["type"] == SAMPLE_TYPE

    def test_unit_scale_is_metres(self, modules):
        """IfcOpenShell normalises geometry to metres whatever the file
        declares (this sample declares millimetres), so the dimensions above are
        metres and the label has to say so."""
        assert modules[0].metadata["unit_scale"] == "METRE"

    def test_room_id_falls_back_when_the_file_has_no_spaces(self, modules):
        """Table 5's RoomID is `IfcSpace.GlobalId`; this sample carries no
        spaces at all, which is common enough that it can't be an error."""
        assert modules[0].metadata["room_id"] == "UNASSIGNED"

    def test_padding_the_file_does_not_change_the_geometry(self):
        """Sizes vary across the suite (they pad the fixture with a comment).
        Metadata is read from the mesh, so it must not move with the byte count."""
        assert extract(ifc_bytes(len(ifc_bytes()) + 500))[0].metadata == extract(
            ifc_bytes()
        )[0].metadata


class TestGlb:
    def test_the_module_carries_glb_bytes(self, modules):
        """A glTF binary starts with the `glTF` magic — this is a real asset,
        not the empty placeholder the stub published."""
        assert modules[0].glb.startswith(b"glTF")

    def test_the_glb_holds_the_merged_geometry(self, modules):
        """Both the wall and the door, in one file. Anything near-empty means
        the merge or an element's mesh was dropped."""
        assert len(modules[0].glb) > 1000


class TestUnrenderableFiles:
    def test_a_file_with_no_geometry_raises(self):
        """Valid IFC, nothing to draw. Raising puts the design in ERROR, where
        the user can see it — the alternative is inventing a module."""
        with pytest.raises(ValueError, match="no renderable geometry"):
            extract(empty_ifc_bytes())

    def test_an_unparseable_file_raises(self):
        with pytest.raises(Exception):  # noqa: B017 — ifcopenshell.Error
            extract(b"this is not an IFC file")

    def test_an_empty_payload_raises(self):
        with pytest.raises(Exception):  # noqa: B017 — ifcopenshell.Error
            extract(b"")


class TestHumanise:
    """Table 5's Type is the IfcElement subtype; the web client renders it
    verbatim, so it gets spaced out rather than shown as a class name."""

    @pytest.mark.parametrize(
        "ifc_class,expected",
        [
            ("IfcWallStandardCase", "Wall Standard Case"),
            ("IfcDoor", "Door"),
            ("IfcSlab", "Slab"),
            ("IfcCurtainWall", "Curtain Wall"),
        ],
    )
    def test_splits_the_class_name(self, ifc_class, expected):
        assert _humanise(ifc_class) == expected
