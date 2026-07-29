"""IFC processor — the extraction SEAM.

This is the plug the IFC-processing team fills. Given a reference to an uploaded
IFC file in blob storage, ``extract`` returns one dict of Table 5 metadata per
extracted module. It does no real IFC work today: it sleeps to mimic a
long-running parse, then fabricates deterministic placeholder modules so the
rest of the pipeline (status lifecycle, module list, GLB URL) is demonstrable
end to end. The worker (``app/processing/worker.py``) calls this off the request.
"""

import time

from ..config import settings

_MODULE_TYPES = [
    "Wall Panel",
    "Bathroom Service Wall",
    "Hospital Headwall",
    "Utility Panel",
]


def _generate_modules(seed: int) -> list[dict]:
    """A single deterministic placeholder module, derived from the file size so a
    given upload is stable. Mirrors the old MSW mock's fabrication."""
    count = 1
    out: list[dict] = []
    for i in range(count):
        s = seed + i * 7
        out.append(
            {
                "type": _MODULE_TYPES[s % len(_MODULE_TYPES)],
                "dimensions": {"x": 2 + (s % 3), "y": 2.4, "z": 0.15 + (s % 2) * 0.1},
                "room_id": f"IfcSpace_{1000 + s}",
                "unit_scale": "METRE",
            }
        )
    return out


def extract(source_ref: str, file_size: int) -> list[dict]:
    """Return the modules extracted from the IFC at ``source_ref`` (a blob key).

    # TODO(processing-team): replace the body below with real IfcOpenShell
    # extraction — open ``source_ref`` from blob storage, walk the elements
    # flagged ``FloorMark.IsMarkingModule``, and emit each one's Table 5
    # metadata (Type, Dimensions, RoomID, Unit Scale, ...) plus its GLB. Until
    # then this sleeps to mimic the parse and fabricates placeholders.
    """
    time.sleep(settings.processing_delay_seconds)
    return _generate_modules(file_size)
