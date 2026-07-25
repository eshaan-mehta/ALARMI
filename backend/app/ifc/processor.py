"""IFC processor — STUB.

Phase 1 does no real IFC work. On upload this fabricates a few placeholder
modules and marks the design COMPLETE synchronously, so the frontend has data
to render. In a later slice this is replaced by IfcOpenShell extraction running
asynchronously off a queue, and status becomes genuinely time-dependent.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from ..modules.models import Module
from ..util import new_id

if TYPE_CHECKING:
    from ..designs.models import Design

_MODULE_TYPES = [
    "Wall Panel",
    "Bathroom Service Wall",
    "Hospital Headwall",
    "Utility Panel",
]


def _generate_modules(seed: int) -> list[dict]:
    """Deterministic placeholder modules (1..3), derived from the file size so a
    given upload is stable. Mirrors the old MSW mock's fabrication."""
    count = 1 + (seed % 3)
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


def process_design(db: Session, design: "Design", file_size: int) -> None:
    """STUB: attach fabricated modules to the design and mark it COMPLETE.
    Does not commit — the caller owns the transaction."""
    for data in _generate_modules(file_size):
        db.add(Module(module_id=new_id("mod"), design_id=design.design_id, **data))
    design.status = "COMPLETE"
