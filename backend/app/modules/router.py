from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import ApiError
from . import repository as repo
from .schemas import UNIT_SCALES, ModuleOut, ModulePatch

router = APIRouter(prefix="/modules", tags=["modules"])


@router.patch("/{module_id}", response_model=ModuleOut)
def update_module(module_id: str, body: ModulePatch, db: Session = Depends(get_db)):
    # Only apply the fields the client actually sent (PATCH semantics).
    # mode="json" flattens the nested Dimensions to a plain dict for storage.
    fields = body.model_dump(exclude_unset=True, mode="json")

    # A module is a physical object — a zero/negative extent isn't a real module.
    if "dimensions" in fields:
        d = fields["dimensions"]
        if any(d[axis] <= 0 for axis in ("x", "y", "z")):
            raise ApiError(400, "Module dimensions must be positive.")

    # The unit must be one the client can convert (see units.ts).
    if "unitScale" in fields and fields["unitScale"] not in UNIT_SCALES:
        raise ApiError(400, "Unsupported unit scale.")

    # A whitespace-only text field clears it rather than storing blank metadata.
    for text_field in ("type", "roomId"):
        if text_field in fields:
            cleaned = (fields[text_field] or "").strip()
            fields[text_field] = cleaned or None

    updated = repo.update_module(db, module_id, fields)
    if updated is None:
        raise ApiError(404, "Module not found.")
    return updated
