from datetime import datetime, timezone
from uuid import uuid4


def new_id(prefix: str) -> str:
    """Opaque, prefixed identifier, e.g. ``prj_a1b2c3d4``. Ids are the identity
    across the system — names are display-only — so they must never be reused."""
    return f"{prefix}_{uuid4().hex[:8]}"


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string, matching the frontend's timestamps."""
    return datetime.now(timezone.utc).isoformat()
