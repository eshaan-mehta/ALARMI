from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import ApiError
from . import repository as repo
from .schemas import ModuleOut, ModulePatch

router = APIRouter(prefix="/modules", tags=["modules"])


@router.patch("/{module_id}", response_model=ModuleOut)
def update_module(module_id: str, body: ModulePatch, db: Session = Depends(get_db)):
    # Only apply the fields the client actually sent (PATCH semantics).
    fields = body.model_dump(exclude_unset=True)
    updated = repo.update_module(db, module_id, fields)
    if updated is None:
        raise ApiError(404, "Module not found.")
    return updated
