from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Module
from .schemas import ModuleOut


def to_module_out(m: Module) -> ModuleOut:
    return ModuleOut(
        moduleId=m.module_id,
        type=m.type,
        dimensions=m.dimensions,
        roomId=m.room_id,
        unitScale=m.unit_scale,
    )


def module_exists(db: Session, module_id: str) -> bool:
    return db.get(Module, module_id) is not None


def design_id_for(db: Session, module_id: str) -> str | None:
    """The design a module belongs to, or None if there's no such module.

    Needed to build the module's GLB key, which is nested under its design.
    """
    m = db.get(Module, module_id)
    return None if m is None else m.design_id


def list_for_design(db: Session, design_id: str) -> list[ModuleOut]:
    rows = db.scalars(select(Module).where(Module.design_id == design_id)).all()
    return [to_module_out(m) for m in rows]


def update_module(db: Session, module_id: str, fields: dict) -> ModuleOut | None:
    m = db.get(Module, module_id)
    if m is None:
        return None
    if "type" in fields:
        m.type = fields["type"]
    if "dimensions" in fields:
        m.dimensions = fields["dimensions"]
    if "roomId" in fields:
        m.room_id = fields["roomId"]
    if "unitScale" in fields:
        m.unit_scale = fields["unitScale"]
    db.commit()
    db.refresh(m)
    return to_module_out(m)
