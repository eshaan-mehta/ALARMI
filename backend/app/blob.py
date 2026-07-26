"""Blob storage seam (Azure Blob).

Uploaded IFC files and the GLBs the processor emits belong in object storage,
not the database or local disk. This slice ships a *fake* store: it accepts
writes, drops the bytes, and hands back a plausible presigned (SAS-style) URL.
Swapping in a real ``AzureBlobStore`` on deploy is a one-line change in
``get_blob_store`` — every caller already speaks the ``put`` / ``url_for``
interface.
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
    real Azure client is a drop-in."""

    def put(self, key: str, data: bytes) -> None: ...

    def url_for(self, key: str) -> str: ...


class FakeBlobStore:
    """Stand-in for Azure Blob until the real client lands. Writes are accepted
    and discarded; ``url_for`` returns a SAS-shaped URL a client can treat
    exactly like a real one (it just won't resolve)."""

    def __init__(self, account: str = "alarmidev", container: str = "alarmi") -> None:
        self._account = account
        self._container = container

    def put(self, key: str, data: bytes) -> None:
        # Bytes intentionally dropped. A real AzureBlobStore streams them into
        # the container; keeping the call site means swapping the impl needs no
        # new wiring at the callers.
        return None

    def url_for(self, key: str) -> str:
        base = f"https://{self._account}.blob.core.windows.net/{self._container}/{key}"
        # Fake SAS token — same shape as an Azure presigned URL, no real
        # signature. The client follows it blindly, so the shape is what matters.
        return f"{base}?sv=2024-11-04&se=2099-01-01T00%3A00%3A00Z&sig=FAKE-SIGNATURE"


class AzureBlobStore:
    """Real Azure Blob store, used when deployed. Uploads bytes to a container
    and hands back a short-lived read SAS URL for the AR viewer to download.

    Auth is via the storage account connection string (account key), injected
    from a Container App secret — no interactive credential needed. The
    ``azure-storage-blob`` package ships only in the ``azure`` extra, so imports
    are local: nothing here is touched during local dev or tests."""

    _SAS_TTL_HOURS = 1

    def __init__(self, connection_string: str, container: str = "alarmi") -> None:
        from azure.storage.blob import BlobServiceClient

        self._svc = BlobServiceClient.from_connection_string(connection_string)
        self._container = container
        self._account = self._svc.account_name
        self._key = self._svc.credential.account_key
        # Idempotent: first deploy creates the container, later ones no-op.
        try:
            self._svc.create_container(container)
        except Exception:  # noqa: BLE001 — already-exists (or race) is fine
            pass

    def put(self, key: str, data: bytes) -> None:
        self._svc.get_blob_client(self._container, key).upload_blob(
            data, overwrite=True
        )

    def url_for(self, key: str) -> str:
        from datetime import datetime, timedelta, timezone

        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        sas = generate_blob_sas(
            account_name=self._account,
            container_name=self._container,
            blob_name=key,
            account_key=self._key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=self._SAS_TTL_HOURS),
        )
        base = f"https://{self._account}.blob.core.windows.net/{self._container}/{key}"
        return f"{base}?{sas}"


@lru_cache(maxsize=1)
def get_blob_store() -> BlobStore:
    """The process-wide blob store. One instance so a real client isn't rebuilt
    per request (and a test spy set on it is seen everywhere).

    Real Azure Blob when a connection string is configured; otherwise the fake
    (local dev + tests), so no Azure account is ever required off-cloud."""
    if settings.azure_storage_connection_string:
        return AzureBlobStore(
            settings.azure_storage_connection_string, settings.blob_container
        )
    return FakeBlobStore()
