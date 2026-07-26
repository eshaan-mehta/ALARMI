"""Unit tests for the blob-storage seam (`app/blob.py`).

Uploaded IFC files and the GLBs the processor emits live in object storage
(Azure Blob), not the database or local disk. This slice ships a *fake* store
that drops the bytes but hands back a plausible presigned URL, so the rest of
the pipeline (upload → process → serve GLB URL) works end to end before the real
Azure client lands. These tests pin the interface every caller depends on.
"""

from app import blob


class TestFakeBlobStore:
    def test_put_accepts_bytes_and_returns_nothing(self):
        assert blob.FakeBlobStore().put("designs/dsn_1/source.ifc", b"ISO-10303-21;") is None

    def test_put_drops_arbitrary_sizes_without_error(self):
        store = blob.FakeBlobStore()
        store.put("empty", b"")
        store.put("largeish", b"x" * 100_000)

    def test_url_for_is_an_absolute_http_url(self):
        assert blob.FakeBlobStore().url_for("modules/mod_1.glb").startswith("http")

    def test_url_embeds_the_key(self):
        url = blob.FakeBlobStore().url_for("modules/mod_abc.glb")
        assert "modules/mod_abc.glb" in url

    def test_url_looks_presigned(self):
        """A presigned Azure URL carries a SAS token in the query string; the
        client just follows it without knowing the account key."""
        url = blob.FakeBlobStore().url_for("modules/mod_1.glb")
        assert "?" in url and "sig=" in url

    def test_distinct_keys_give_distinct_urls(self):
        store = blob.FakeBlobStore()
        assert store.url_for("modules/a.glb") != store.url_for("modules/b.glb")


class TestKeyHelpers:
    def test_source_key_is_scoped_to_the_design(self):
        assert blob.source_key("dsn_1") == "designs/dsn_1/source.ifc"

    def test_glb_key_is_scoped_to_the_module(self):
        assert blob.glb_key("mod_1") == "modules/mod_1.glb"


class TestGetBlobStore:
    def test_returns_a_store_with_the_interface(self):
        store = blob.get_blob_store()
        assert hasattr(store, "put") and hasattr(store, "url_for")

    def test_is_a_singleton(self):
        """One store instance per process, so a spy set on it in one place is
        seen everywhere (and so a real client isn't rebuilt per request)."""
        assert blob.get_blob_store() is blob.get_blob_store()
