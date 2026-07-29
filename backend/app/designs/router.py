from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from .. import blob
from ..db import get_db
from ..errors import ApiError
from ..modules.schemas import ModuleOut
from ..processing import queue
from . import repository as repo
from .schemas import DesignOut, DesignRename, StatusOut

# No prefix: these routes span two resource paths (/projects/{id}/designs and
# /designs/{id}), so each declares its full path.
router = APIRouter(tags=["designs"])

_ONE_GB = 1024**3


@router.get("/projects/{project_id}/designs", response_model=list[DesignOut])
def list_designs(project_id: str, db: Session = Depends(get_db)):
    # Distinguish an unknown/deleted project from a real but empty one.
    if not repo.project_exists(db, project_id):
        raise ApiError(404, "Project not found.")
    return repo.list_designs(db, project_id)


@router.post(
    "/projects/{project_id}/designs", response_model=DesignOut, status_code=201
)
def upload_design(
    project_id: str,
    background_tasks: BackgroundTasks,
    name: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if file is None:
        raise ApiError(400, "A file is required.")
    filename = file.filename or ""
    size = file.size or 0
    if size == 0:
        raise ApiError(400, "The file is empty.")
    if size > _ONE_GB:
        raise ApiError(400, "File exceeds the 1 GB limit.")

    design_name = name.strip() or filename
    created = repo.create_design(db, project_id, design_name, filename, size)
    if created is None:
        raise ApiError(404, "Project not found.")

    # Stash the source in blob storage (fake: bytes dropped), then hand
    # extraction to the background so the upload returns immediately with status
    # PROCESSING. The client polls /status until the worker settles it.
    # NOTE: these actions must always remain sequential to avoid a race condition where the worker tries to read the blob before it is written.
    blob.get_blob_store().put(blob.source_key(created.designId), file.file.read())
    queue.enqueue(background_tasks, created.designId)
    return created


@router.get("/designs/{design_id}", response_model=DesignOut)
def get_design(design_id: str, db: Session = Depends(get_db)):
    design = repo.get_design(db, design_id)
    if design is None:
        raise ApiError(404, "Design not found.")
    return design


@router.patch("/designs/{design_id}", response_model=DesignOut)
def rename_design(design_id: str, body: DesignRename, db: Session = Depends(get_db)):
    fields = body.model_dump(exclude_unset=True)
    if "name" in fields:
        cleaned = (fields["name"] or "").strip()
        if not cleaned:
            raise ApiError(400, "Design name is required.")
        fields["name"] = cleaned
    updated = repo.update_design(db, design_id, fields)
    if updated is None:
        raise ApiError(404, "Design not found.")
    return updated


@router.delete("/designs/{design_id}", status_code=204)
def delete_design(design_id: str, db: Session = Depends(get_db)):
    if not repo.delete_design(db, design_id):
        raise ApiError(404, "Design not found.")
    return Response(status_code=204)


@router.get("/designs/{design_id}/status", response_model=StatusOut)
def design_status(design_id: str, db: Session = Depends(get_db)):
    status = repo.get_status(db, design_id)
    if status is None:
        raise ApiError(404, "Design not found.")
    return StatusOut(status=status)


@router.get("/designs/{design_id}/modules", response_model=list[ModuleOut])
def design_modules(design_id: str, db: Session = Depends(get_db)):
    modules = repo.list_modules(db, design_id)
    if modules is None:
        raise ApiError(404, "Design not found.")
    return modules
