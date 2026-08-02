"""Blob storage seam (Google Cloud Storage).

Uploaded IFC files and the GLBs the processor emits belong in object storage,
not the database or local disk. This slice ships a *fake* store: it accepts
writes, drops the bytes, and hands back a plausible V4-signed URL. Swapping in a
real ``GcsBlobStore`` on deploy is a one-line change in ``get_blob_store`` —
every caller already speaks the ``put`` / ``url_for`` interface.

Everything a design owns lives under one prefix::

    designs/{designId}/{original-filename}.ifc   the uploaded source
    designs/{designId}/modules/{moduleId}.glb    one GLB per extracted module

so deleting a design is a single prefix wipe and no object is ever unattributable.
"""

import logging
import re
from functools import lru_cache
from typing import Protocol

from .config import settings

logger = logging.getLogger("alarmi")

# Control characters are illegal-ish in GCS object names and invisible in a
# listing; everything else the user typed is kept.
_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_FALLBACK_NAME = "source.ifc"
# GCS caps object names at 1024 bytes UTF-8. Leave generous room for the prefix.
_MAX_NAME_BYTES = 512


def safe_filename(filename: str) -> str:
    """The uploaded filename, reduced to something usable as a GCS object name.

    Deliberately minimal: the point of keying by filename is that the bucket
    listing reads like the user's uploads, so only characters that change the
    *shape* of the key are touched. A '/' in an object name silently creates
    another level of pseudo-directory (``Floor 1/rev 2.ifc`` would land inside
    the design's prefix as a subfolder), so paths are reduced to their last
    segment. Spaces, unicode, parentheses all survive verbatim.
    """
    name = _UNSAFE_CHARS.sub("", filename.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    # '', '.', '..' leave nothing to key on.
    if not name.strip("."):
        return _FALLBACK_NAME
    if len(name.encode("utf-8")) > _MAX_NAME_BYTES:
        stem, dot, ext = name.rpartition(".")
        if not dot:
            stem, ext = name, ""
        budget = _MAX_NAME_BYTES - len(ext.encode("utf-8")) - 1
        stem = stem.encode("utf-8")[: max(budget, 1)].decode("utf-8", "ignore")
        name = f"{stem}.{ext}" if ext else stem
    return name


def design_prefix(design_id: str) -> str:
    """Everything a design owns — its source and all its modules' GLBs."""
    return f"designs/{design_id}/"


def source_key(design_id: str, filename: str) -> str:
    """Blob key for a design's uploaded IFC source.

    The original filename is kept so the bucket listing is readable. Uniqueness
    comes from the design id prefix, not the name, so two uploads both called
    ``model.ifc`` can't collide.
    """
    return f"{design_prefix(design_id)}{safe_filename(filename)}"


def glb_key(design_id: str, module_id: str) -> str:
    """Blob key for a module's GLB — what the AR viewer downloads."""
    return f"{design_prefix(design_id)}modules/{module_id}.glb"


def is_source_key(key: str, design_id: str) -> bool:
    """True for an object sitting *directly* under the design's prefix.

    The source is the only thing there — GLBs are one level deeper, under
    ``modules/`` — which is what lets ``source_ref`` find the upload without
    knowing its name.
    """
    prefix = design_prefix(design_id)
    return key.startswith(prefix) and "/" not in key[len(prefix) :]


def _exactly_one_source(design_id: str, names: list[str]) -> str:
    """The design's single source object, or a loud failure.

    'One source per design' holds because the upload endpoint is the only writer,
    but nothing in the bucket enforces it. If a replace-file flow, a partial
    retry, or a new per-design artifact ever lands here, silently taking the
    first name would read the wrong bytes — so this raises instead.
    """
    if len(names) != 1:
        raise LookupError(
            f"expected exactly 1 source object under {design_prefix(design_id)}, "
            f"found {len(names)}: {sorted(names)[:5]}"
        )
    return names[0]


class BlobStore(Protocol):
    """What the rest of the app needs from object storage. Small on purpose so a
    real GCS client is a drop-in."""

    def put(self, key: str, data: bytes) -> None: ...

    def url_for(self, key: str) -> str: ...

    def source_ref(self, design_id: str) -> str: ...

    def delete_prefix(self, prefix: str) -> int: ...


class FakeBlobStore:
    """Stand-in for GCS until the real client lands. Bytes are accepted and
    discarded; ``url_for`` returns a signed-URL-shaped link a client can treat
    exactly like a real one (it just won't resolve).

    Keys *are* retained — only the payloads are dropped — so ``source_ref`` and
    ``delete_prefix`` answer the same questions the real store answers with a
    list call, and local dev exercises those paths for real."""

    def __init__(self, bucket: str = "alarmi") -> None:
        self._bucket = bucket
        self._keys: set[str] = set()

    def put(self, key: str, data: bytes) -> None:
        # Payload intentionally dropped. A real GcsBlobStore streams it into the
        # bucket; keeping the call site means swapping the impl needs no new
        # wiring at the callers.
        self._keys.add(key)

    def url_for(self, key: str) -> str:
        base = f"https://storage.googleapis.com/{self._bucket}/{key}"
        # Fake V4 signature — same shape as a GCS signed URL, no real signature.
        # The client follows it blindly, so the shape is what matters.
        return (
            f"{base}?X-Goog-Algorithm=GOOG4-RSA-SHA256"
            f"&X-Goog-Expires=3600&X-Goog-Signature=FAKE-SIGNATURE"
        )

    def source_ref(self, design_id: str) -> str:
        return _exactly_one_source(
            design_id, [k for k in self._keys if is_source_key(k, design_id)]
        )

    def delete_prefix(self, prefix: str) -> int:
        doomed = {k for k in self._keys if k.startswith(prefix)}
        self._keys -= doomed
        return len(doomed)


class GcsBlobStore:
    """Real Google Cloud Storage store, used when deployed to Cloud Run. Uploads
    bytes to a bucket and hands back a short-lived V4 signed URL for the AR
    viewer to download.

    Auth is Application Default Credentials — the Cloud Run service account. No
    key file: the signed URL is produced via the IAM SignBlob API, so the
    service account only needs ``roles/iam.serviceAccountTokenCreator`` on
    itself. The ``google-cloud-storage`` package ships only in the ``gcp``
    extra, so imports are local: nothing here is touched during local dev/tests.
    """

    _URL_TTL_HOURS = 1

    def __init__(self, bucket: str) -> None:
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)

    def put(self, key: str, data: bytes) -> None:
        self._bucket.blob(key).upload_from_string(data)

    def url_for(self, key: str) -> str:
        from datetime import timedelta

        import google.auth
        from google.auth.transport import requests as ga_requests

        # ADC on Cloud Run carries no private key, so sign via the IAM SignBlob
        # API: refresh to mint an access token + read the SA email, then let the
        # storage client call SignBlob for us.
        creds, _ = google.auth.default()
        creds.refresh(ga_requests.Request())
        return self._bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=timedelta(hours=self._URL_TTL_HOURS),
            method="GET",
            service_account_email=creds.service_account_email,
            access_token=creds.token,
        )

    def source_ref(self, design_id: str) -> str:
        # delimiter="/" makes GCS return only direct children; the modules/
        # subtree comes back as a prefix rather than as blobs, so the source is
        # the sole result.
        prefix = design_prefix(design_id)
        blobs = self._bucket.list_blobs(prefix=prefix, delimiter="/")
        return _exactly_one_source(design_id, [b.name for b in blobs])

    def delete_prefix(self, prefix: str) -> int:
        deleted = 0
        for b in self._bucket.list_blobs(prefix=prefix):
            b.delete()
            deleted += 1
        return deleted


@lru_cache(maxsize=1)
def get_blob_store() -> BlobStore:
    """The process-wide blob store. One instance so a real client isn't rebuilt
    per request (and a test spy set on it is seen everywhere).

    Real GCS when a bucket is configured; otherwise the fake (local dev + tests),
    so no GCP account is ever required off-cloud."""
    if settings.gcs_bucket:
        return GcsBlobStore(settings.gcs_bucket)
    return FakeBlobStore()
