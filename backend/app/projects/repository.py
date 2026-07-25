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


def project_name_exists(db: Session, name: str) -> bool:
    return db.scalar(select(Project).where(Project.name == name)) is not None


def create_project(db: Session, name: str, location: str) -> ProjectOut:
    p = Project(
        project_id=new_id("prj"), name=name, location=location, created_time=now_iso()
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return to_project_out(db, p)


def rename_project(db: Session, project_id: str, new_name: str) -> ProjectOut | None:
    p = db.get(Project, project_id)
    if p is None:
        return None
    p.name = new_name  # identity is the id, so a rename is a single field update
    db.commit()
    db.refresh(p)
    return to_project_out(db, p)
