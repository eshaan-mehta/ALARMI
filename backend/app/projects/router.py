from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import ApiError
from . import repository as repo
from .schemas import ProjectCreate, ProjectOut, ProjectRename

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/all_projects", response_model=list[ProjectOut])
def all_projects(db: Session = Depends(get_db)):
    return repo.list_projects(db)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    name = (body.name or "").strip()
    location = (body.location or "").strip()
    if not name:
        raise ApiError(400, "Project name is required.")
    if not location:
        raise ApiError(400, "Project location is required.")
    if repo.project_name_exists(db, name):
        raise ApiError(409, "A project with that name already exists.")
    return repo.create_project(db, name, location)


@router.patch("/{project_id}", response_model=ProjectOut)
def rename_project(project_id: str, body: ProjectRename, db: Session = Depends(get_db)):
    new_name = (body.new_name or "").strip()
    if not new_name:
        raise ApiError(400, "new_name is required.")
    updated = repo.rename_project(db, project_id, new_name)
    if updated is None:
        raise ApiError(404, "Project not found.")
    return updated
