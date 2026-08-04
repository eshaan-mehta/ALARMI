"""The processing job.

``run_job`` is what actually turns an uploaded design into modules: it reads the
uploaded IFC back from blob storage, hands it to the extractor seam, persists
the extracted metadata, publishes each module's GLB to blob storage, and moves
the design into a terminal status (COMPLETE or ERROR).

It runs *off* the request (enqueued via ``queue.enqueue``), so it opens its own
DB session — the request that scheduled it has already returned and closed its
session. Failures are recorded on the design, never raised: a background task
has no caller to hand an exception to.
"""

import logging

from ..blob import get_blob_store, glb_key, source_key
from ..db import SessionLocal
from ..designs.models import Design
from ..ifc import processor
from ..modules.models import Module
from ..util import new_id, now_iso

logger = logging.getLogger("alarmi")


def run_job(design_id: str) -> None:
    db = SessionLocal()
    try:
        design = db.get(Design, design_id)
        if design is None:
            # Deleted between enqueue and run — nothing to process.
            return
        try:
            store = get_blob_store()
            # The upload handler wrote the source before enqueuing this job, so
            # the bytes are there to be read back.
            source = store.get(source_key(design_id, design.file_name))
            for module in processor.extract(source):
                module_id = new_id("mod")
                db.add(Module(module_id=module_id, design_id=design_id, **module.metadata))
                # Publish the module's GLB for the AR viewer to download via
                # /objects/get_url/{moduleId}.
                store.put(glb_key(design_id, module_id), module.glb)
            design.status = "COMPLETE"
            design.processed_time = now_iso()
            design.error = None
            db.commit()
        except Exception as exc:  # noqa: BLE001 — recorded on the design below
            db.rollback()
            logger.exception("Processing failed for %s", design_id)
            design = db.get(Design, design_id)
            if design is not None:
                design.status = "ERROR"
                design.error = str(exc)[:500]
                design.processed_time = now_iso()
                db.commit()
    finally:
        db.close()
