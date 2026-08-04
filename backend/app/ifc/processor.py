"""IFC processor — IfcOpenShell geometry in, GLB out.

Given the bytes of an uploaded IFC, ``extract`` returns one
:class:`ExtractedModule` per module: the Table 5 metadata the API serves plus
the GLB the AR viewer renders. The worker (``app/processing/worker.py``) calls
this off the request, reading the source from blob storage and writing each GLB
back to it.

Demo-grade on purpose. The real pipeline emits one module per element flagged
``FloorMark.IsMarkingModule``; nothing writes that flag yet, so every renderable
element in the file is merged into a *single* module whose GLB is the whole
design. Metadata is read off that merged mesh rather than fabricated.

Anything that leaves nothing to render — an unparseable file, or a valid IFC
with no drawable elements — raises, which the worker turns into a design in
status ERROR. Emitting a plausible-looking module for a file we couldn't read
would be worse than failing: the user would take the metadata at face value.
"""

import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np
import trimesh

logger = logging.getLogger("alarmi")

# Openings are voids (rendering one would fill the doorway back in) and spaces
# are volumes of air — neither is a thing the viewer should draw.
_NOT_RENDERABLE = ("IfcOpeningElement", "IfcSpace")

# Faces the file gives no material. Mid-grey, fully opaque.
_DEFAULT_FACE_COLOR = (0.7, 0.7, 0.7, 1.0)

# IfcOpenShell returns geometry in metres whatever length unit the file
# declares, so the dimensions below are metres and the module says so. Reading
# IfcProject.UnitsInContext instead would label the numbers with a unit they are
# not in.
_GEOMETRY_UNIT_SCALE = "METRE"

# Table 5's RoomID is IfcSpace.GlobalId; plenty of real files (and every
# single-element sample) carry no spaces at all.
_UNPLACED_ROOM = "UNASSIGNED"

# A perfectly planar design would extract a zero-thickness axis, which reads as
# "no module" to the AR overlay and the robot's footprint. Floor it at 1 mm.
_MIN_EXTENT_M = 0.001


@dataclass(frozen=True)
class ExtractedModule:
    """One module: its Table 5 metadata (keyed to match ``Module``'s columns, so
    the worker can splat it into the model) and the GLB bytes for its geometry."""

    metadata: dict
    glb: bytes


def _humanise(ifc_class: str) -> str:
    """``IfcWallStandardCase`` -> ``Wall Standard Case`` — Table 5's Type is the
    IfcElement subtype, and the web client renders it verbatim."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", ifc_class.removeprefix("Ifc")).strip()


def _mesh_for(geom_settings, element) -> trimesh.Trimesh:
    """The element's triangulated geometry, coloured by its IFC materials."""
    # `shape` has to stay in scope: `shape.geometry` is a view into it, and
    # `create_shape(...).geometry` reads back empty once the shape is collected.
    shape = ifcopenshell.geom.create_shape(geom_settings, element)
    geometry = shape.geometry
    vertices = np.array(geometry.verts).reshape(-1, 3)
    faces = np.array(geometry.faces).reshape(-1, 3)

    materials = geometry.materials
    material_ids = np.array(geometry.material_ids)
    face_colors = np.full((len(faces), 4), _DEFAULT_FACE_COLOR)
    for mid in np.unique(material_ids):
        if mid < 0:  # -1 marks a face the file assigns no material
            continue
        diffuse = materials[mid].diffuse
        face_colors[material_ids == mid] = (
            diffuse.r(),
            diffuse.g(),
            diffuse.b(),
            1.0 - materials[mid].transparency,
        )

    # process=False keeps IfcOpenShell's vertices as they are: merging them
    # would weld faces that carry different materials.
    return trimesh.Trimesh(
        vertices=vertices, faces=faces, face_colors=face_colors, process=False
    )


def _renderable_meshes(ifc_file) -> list[tuple[str, trimesh.Trimesh]]:
    """Every drawable element in the file, as ``(ifc_class, mesh)``.

    One element failing to build is logged and skipped rather than failing the
    upload — a single unsupported representation in a large model shouldn't cost
    the user the other few hundred elements.
    """
    geom_settings = ifcopenshell.geom.settings()
    geom_settings.set("use-world-coords", True)  # each element in model space

    out: list[tuple[str, trimesh.Trimesh]] = []
    for element in ifc_file.by_type("IfcProduct"):
        if not element.Representation:
            continue
        if any(element.is_a(cls) for cls in _NOT_RENDERABLE):
            continue
        try:
            mesh = _mesh_for(geom_settings, element)
            # An element can carry a representation that triangulates to nothing
            # (annotations, 2D curves). An empty mesh has no extents to weigh or
            # merge, so it never reaches the rest of the pipeline.
            if len(mesh.faces):
                out.append((element.is_a(), mesh))
        except Exception:  # noqa: BLE001 — one bad element, not a bad file
            logger.warning(
                "Skipped %s %s: geometry could not be built",
                element.is_a(),
                element.GlobalId,
                exc_info=True,
            )
    return out


def _dominant_type(meshes: list[tuple[str, trimesh.Trimesh]]) -> str:
    """The module's Type: the IFC class taking up the most space.

    Weighted by bounding-box volume rather than triangle count — a door is
    modelled in far more detail than the wall it sits in, so counting faces would
    label the module after its fussiest fixture instead of its bulk. Bounding
    boxes (not ``mesh.volume``) because element meshes aren't reliably watertight.
    """
    weight: dict[str, float] = {}
    for ifc_class, mesh in meshes:
        weight[ifc_class] = weight.get(ifc_class, 0.0) + float(mesh.extents.prod())
    return _humanise(max(weight, key=weight.get))


def _room_id(ifc_file) -> str:
    spaces = ifc_file.by_type("IfcSpace")
    return spaces[0].GlobalId if spaces else _UNPLACED_ROOM


def _dimensions(mesh: trimesh.Trimesh) -> dict:
    """The mesh's bounding-box extents, in metres.

    Read *before* the Y-up rotation below, so x/y/z stay the IFC file's own axes
    (z is height) rather than glTF's.
    """
    x, y, z = (max(float(e), _MIN_EXTENT_M) for e in mesh.extents)
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}


def extract(source: bytes) -> list[ExtractedModule]:
    """The modules in ``source`` (the raw bytes of an uploaded IFC file).

    Raises if the file can't be parsed or holds nothing renderable — the design
    belongs in ERROR, not in COMPLETE with invented metadata.
    """
    # IfcOpenShell reads from a path, and doing so lets it handle the file's own
    # encoding instead of us guessing one to decode the bytes with.
    with tempfile.TemporaryDirectory(prefix="alarmi-ifc-") as tmp:
        path = Path(tmp) / "source.ifc"
        path.write_bytes(source)
        ifc_file = ifcopenshell.open(str(path))

        meshes = _renderable_meshes(ifc_file)
        if not meshes:
            raise ValueError(
                "The IFC file contains no renderable geometry — nothing to extract."
            )

        merged = trimesh.util.concatenate([mesh for _, mesh in meshes])
        metadata = {
            "type": _dominant_type(meshes),
            "dimensions": _dimensions(merged),
            "room_id": _room_id(ifc_file),
            "unit_scale": _GEOMETRY_UNIT_SCALE,
        }

    # IFC is Z-up; glTF requires Y-up. Rotate -90 deg about X to convert.
    merged.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    glb = merged.export(file_type="glb")

    logger.info(
        "Extracted 1 module from %d elements: %d vertices, %d faces, %d GLB bytes",
        len(meshes),
        len(merged.vertices),
        len(merged.faces),
        len(glb),
    )
    return [ExtractedModule(metadata=metadata, glb=glb)]
