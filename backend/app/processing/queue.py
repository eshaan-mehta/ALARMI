"""The enqueue seam.

Today "enqueue" is a FastAPI background task in the same process, which the
upload handler schedules and the server runs after the response is sent. On
Azure this becomes a message on a Storage Queue that a separate worker drains —
only this function changes; the handler that calls it does not.
"""

from fastapi import BackgroundTasks

from .worker import run_job


def enqueue(background_tasks: BackgroundTasks, design_id: str) -> None:
    # TODO(deploy): publish design_id to an Azure Storage Queue instead of
    # running it in-process, and drain the queue from a separate worker.
    background_tasks.add_task(run_job, design_id)
