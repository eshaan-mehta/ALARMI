"""Blob storage seam (Google Cloud Storage).

Uploaded IFC files and the GLBs the processor emits belong in object storage,
not the database or local disk. This slice ships a *fake* store: it accepts
writes, drops the bytes, and hands back a plausible V4-signed URL. Swapping in a
real ``GcsBlobStore`` on deploy is a one-line change in ``get_blob_store`` —
every caller already speaks the ``put`` / ``url_for`` interface.
"""

from functools import lru_cache
from typing import Protocol

from .config import settings


def source_key(design_id: str) -> str:
    """Blob key for a design's uploaded IFC source."""
    return f"designs/{design_id}/source.ifc"


def glb_key(module_id: str) -> str:
    """Blob key for a module's GLB — what the AR viewer downloads."""
    return f"modules/{module_id}.glb"


class BlobStore(Protocol):
    """What the rest of the app needs from object storage. Small on purpose so a
    real GCS client is a drop-in."""

    def put(self, key: str, data: bytes) -> None: ...

    def url_for(self, key: str) -> str: ...


class FakeBlobStore:
    """Stand-in for GCS until the real client lands. Writes are accepted and
    discarded; ``url_for`` returns a signed-URL-shaped link a client can treat
    exactly like a real one (it just won't resolve)."""

    def __init__(self, bucket: str = "alarmi") -> None:
        self._bucket = bucket

    def put(self, key: str, data: bytes) -> None:
        # Bytes intentionally dropped. A real GcsBlobStore streams them into the
        # bucket; keeping the call site means swapping the impl needs no new
        # wiring at the callers.
        return None

    def url_for(self, key: str) -> str:
        base = f"https://storage.googleapis.com/{self._bucket}/{key}"
        # Fake V4 signature — same shape as a GCS signed URL, no real signature.
        # The client follows it blindly, so the shape is what matters.
        return (
            f"{base}?X-Goog-Algorithm=GOOG4-RSA-SHA256"
            f"&X-Goog-Expires=3600&X-Goog-Signature=FAKE-SIGNATURE"
        )


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


@lru_cache(maxsize=1)
def get_blob_store() -> BlobStore:
    """The process-wide blob store. One instance so a real client isn't rebuilt
    per request (and a test spy set on it is seen everywhere).

    Real GCS when a bucket is configured; otherwise the fake (local dev + tests),
    so no GCP account is ever required off-cloud."""
    if settings.gcs_bucket:
        return GcsBlobStore(settings.gcs_bucket)
    return FakeBlobStore()
