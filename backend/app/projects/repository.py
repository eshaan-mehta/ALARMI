from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..designs.models import Design
from ..util import new_id, now_iso
from .models import Project
from .schemas import ProjectOut


def _design_count(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Design).where(Design.project_id == project_id)
    )


def to_project_out(db: Session, p: Project) -> ProjectOut:
    return ProjectOut(
        projectId=p.project_id,
        name=p.name,
        location=p.location,
        designCount=_design_count(db, p.project_id),
        createdTime=p.created_time,
    )


def list_projects(db: Session) -> list[ProjectOut]:
    rows = db.scalars(select(Project).order_by(Project.created_time.desc())).all()
    return [to_project_out(db, p) for p in rows]


def _by_name(db: Session, name: str) -> Project | None:
    """Look a project up by display name, the way a person reads it: case and
    surrounding whitespace don't make it a different project. SQLite compares
    strings byte-exactly, so the normalisation has to be explicit here."""
    return db.scalar(
        select(Project).where(func.lower(Project.name) == name.strip().lower())
    )


def project_name_exists(db: Session, name: str) -> bool:
    return _by_name(db, name) is not None


def project_exists(db: Session, project_id: str) -> bool:
    return db.get(Project, project_id) is not None


def name_taken_by_other(db: Session, name: str, project_id: str) -> bool:
    """True if `name` belongs to a different project — so a rename onto it is a
    conflict (renaming a project to its own current name is fine)."""
    p = _by_name(db, name)
    return p is not None and p.project_id != project_id


def create_project(db: Session, name: str, location: str) -> ProjectOut:
    p = Project(
        project_id=new_id("prj"), name=name, location=location, created_time=now_iso()
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return to_project_out(db, p)


def processing_design_count(db: Session, project_id: str) -> int:
    """Designs still being extracted. A project can't be deleted while any exist:
    the worker settles the design's status and writes its GLBs *after* the
    request returns, so deleting underneath it loses that write and strands the
    blobs it is still producing."""
    return db.scalar(
        select(func.count())
        .select_from(Design)
        .where(Design.project_id == project_id, Design.status == "PROCESSING")
    )


def rename_project(db: Session, project_id: str, new_name: str) -> ProjectOut | None:
    p = db.get(Project, project_id)
    if p is None:
        return None
    p.name = new_name  # identity is the id, so a rename is a single field update
    db.commit()
    db.refresh(p)
    return to_project_out(db, p)


def delete_project(db: Session, project_id: str) -> list[str] | None:
    """Deletes a project and everything under it.

    Returns the ids of the designs that went with it — blobs are keyed per
    design, so the caller needs them to clean storage — or ``None`` if the
    project doesn't exist."""
    p = db.get(Project, project_id)
    if p is None:
        return None
    design_ids = [d.design_id for d in p.designs]
    db.delete(p)  # cascade removes the designs, then their modules
    db.commit()
    return design_ids
