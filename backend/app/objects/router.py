from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..blob import get_blob_store, glb_key
from ..db import get_db
from ..errors import ApiError
from ..modules import repository as modules_repo
from .schemas import ObjectUrlOut

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("/get_url/{module_id}", response_model=ObjectUrlOut)
def get_object_url(module_id: str, db: Session = Depends(get_db)):
    """Presigned URL to a module's GLB (design doc Table 4). The mobile app
    follows it to render the module in AR; web clients don't need it — they show
    metadata in a modal."""
    design_id = modules_repo.design_id_for(db, module_id)
    if design_id is None:
        raise ApiError(404, "Module not found.")
    return ObjectUrlOut(url=get_blob_store().url_for(glb_key(design_id, module_id)))
