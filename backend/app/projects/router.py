import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import blob
from ..db import get_db
from ..errors import ApiError
from . import repository as repo
from .schemas import ProjectCreate, ProjectOut, ProjectRename

logger = logging.getLogger("alarmi")

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
    if not repo.project_exists(db, project_id):
        raise ApiError(404, "Project not found.")
    if repo.name_taken_by_other(db, new_name, project_id):
        raise ApiError(409, "A project with that name already exists.")
    updated = repo.rename_project(db, project_id, new_name)
    if updated is None:
        raise ApiError(404, "Project not found.")
    return updated


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    if not repo.project_exists(db, project_id):
        raise ApiError(404, "Project not found.")
    if repo.processing_design_count(db, project_id):
        raise ApiError(409, "Can't delete a project while a design is still processing.")
    design_ids = repo.delete_project(db, project_id)
    if design_ids is None:
        raise ApiError(404, "Project not found.")
    # Blobs live under a per-design prefix (designs/{designId}/) — there is no
    # project-level prefix — so each design's objects are wiped separately.
    # Deliberately after the DB delete, as in delete_design: if storage fails
    # we're left with orphaned blobs (recoverable) rather than rows pointing at
    # bytes that are already gone.
    store = blob.get_blob_store()
    for design_id in design_ids:
        try:
            store.delete_prefix(blob.design_prefix(design_id))
        except Exception:  # noqa: BLE001 — the project *is* deleted; don't fail the request
            logger.exception("Blob cleanup failed for %s", design_id)
    return Response(status_code=204)
