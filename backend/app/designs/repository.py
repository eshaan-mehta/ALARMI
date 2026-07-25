from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ifc.processor import process_design
from ..modules import repository as modules_repo
from ..modules.models import Module
from ..modules.schemas import ModuleOut
from ..projects.models import Project
from ..util import new_id, now_iso
from .models import Design
from .schemas import DesignOut


def _module_count(db: Session, design_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Module).where(Module.design_id == design_id)
    )


def to_design_out(db: Session, d: Design) -> DesignOut:
    # Module count is only meaningful once processing is COMPLETE.
    count = _module_count(db, d.design_id) if d.status == "COMPLETE" else 0
    return DesignOut(
        designId=d.design_id,
        projectId=d.project_id,
        name=d.name,
        fileName=d.file_name,
        fileSize=d.file_size,
        status=d.status,
        uploadTime=d.upload_time,
        moduleCount=count,
    )


def list_designs(db: Session, project_id: str) -> list[DesignOut]:
    rows = db.scalars(
        select(Design)
        .where(Design.project_id == project_id)
        .order_by(Design.upload_time.desc())
    ).all()
    return [to_design_out(db, d) for d in rows]


def get_design(db: Session, design_id: str) -> DesignOut | None:
    d = db.get(Design, design_id)
    return to_design_out(db, d) if d else None


def get_status(db: Session, design_id: str) -> str | None:
    d = db.get(Design, design_id)
    return d.status if d else None


def list_modules(db: Session, design_id: str) -> list[ModuleOut] | None:
    """Returns the design's modules, or ``None`` if the design doesn't exist so
    the router can 404. Empty list until the design is COMPLETE."""
    d = db.get(Design, design_id)
    if d is None:
        return None
    if d.status != "COMPLETE":
        return []
    return modules_repo.list_for_design(db, design_id)


def create_design(
    db: Session, project_id: str, name: str, file_name: str, file_size: int
) -> DesignOut | None:
    """Creates a design and runs the stub processor. Returns ``None`` if the
    parent project doesn't exist."""
    if db.get(Project, project_id) is None:
        return None
    d = Design(
        design_id=new_id("dsn"),
        project_id=project_id,
        name=name,
        file_name=file_name,
        file_size=file_size,
        status="PROCESSING",
        upload_time=now_iso(),
    )
    db.add(d)
    process_design(db, d, file_size)  # stub: fabricates modules, marks COMPLETE
    db.commit()
    db.refresh(d)
    return to_design_out(db, d)


def update_design(db: Session, design_id: str, fields: dict) -> DesignOut | None:
    d = db.get(Design, design_id)
    if d is None:
        return None
    if "name" in fields:
        d.name = fields["name"]
    db.commit()
    db.refresh(d)
    return to_design_out(db, d)


def delete_design(db: Session, design_id: str) -> bool:
    d = db.get(Design, design_id)
    if d is None:
        return False
    db.delete(d)  # cascade removes the design's modules
    db.commit()
    return True
