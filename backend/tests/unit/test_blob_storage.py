"""Unit tests for the blob-storage seam (`app/blob.py`).

Uploaded IFC files and the GLBs the processor emits live in object storage
(Google Cloud Storage), not the database or local disk. This slice ships a
*fake* store that drops the bytes but hands back a plausible signed URL, so the
rest of the pipeline (upload → process → serve GLB URL) works end to end before
the real GCS client lands. These tests pin the interface every caller depends on.
"""

import pytest

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
        """A GCS signed URL carries a signature in the query string; the client
        just follows it without knowing any account key."""
        url = blob.FakeBlobStore().url_for("modules/mod_1.glb")
        assert "?" in url and "X-Goog-Signature=" in url

    def test_distinct_keys_give_distinct_urls(self):
        store = blob.FakeBlobStore()
        assert store.url_for("modules/a.glb") != store.url_for("modules/b.glb")


class TestKeyHelpers:
    def test_source_key_keeps_the_uploaded_filename(self):
        assert blob.source_key("dsn_1", "ward-a.ifc") == "designs/dsn_1/ward-a.ifc"

    def test_glb_key_is_nested_under_its_design(self):
        """A design's objects share one prefix, so deleting the design is a
        single prefix wipe and no GLB is ever unattributable."""
        assert blob.glb_key("dsn_1", "mod_1") == "designs/dsn_1/modules/mod_1.glb"

    def test_same_filename_in_two_designs_does_not_collide(self):
        """Uniqueness comes from the design id, not the name."""
        assert blob.source_key("dsn_1", "model.ifc") != blob.source_key("dsn_2", "model.ifc")

    def test_design_prefix_covers_source_and_modules(self):
        prefix = blob.design_prefix("dsn_1")
        assert blob.source_key("dsn_1", "a.ifc").startswith(prefix)
        assert blob.glb_key("dsn_1", "mod_1").startswith(prefix)

    def test_only_the_source_sits_directly_under_the_prefix(self):
        assert blob.is_source_key(blob.source_key("dsn_1", "a.ifc"), "dsn_1")
        assert not blob.is_source_key(blob.glb_key("dsn_1", "mod_1"), "dsn_1")
        assert not blob.is_source_key(blob.source_key("dsn_2", "a.ifc"), "dsn_1")


class TestSafeFilename:
    def test_ordinary_names_pass_through_untouched(self):
        assert blob.safe_filename("ward-a.ifc") == "ward-a.ifc"

    def test_spaces_and_unicode_survive(self):
        """Only characters that change the key's *shape* are stripped."""
        assert blob.safe_filename("Étage 1 (rev 2).ifc") == "Étage 1 (rev 2).ifc"

    def test_path_separators_are_reduced_to_the_last_segment(self):
        """A '/' would silently add a pseudo-directory inside the design prefix."""
        assert blob.safe_filename("Floor 1/rev 2.ifc") == "rev 2.ifc"
        assert blob.safe_filename(r"C:\models\ward.ifc") == "ward.ifc"

    def test_control_characters_are_dropped(self):
        assert blob.safe_filename("wa\x00rd\x1f.ifc") == "ward.ifc"

    def test_names_with_nothing_left_fall_back(self):
        for empty in ("", "   ", ".", "..", "/", "///"):
            assert blob.safe_filename(empty) == "source.ifc"

    def test_absurd_names_are_truncated_but_keep_the_extension(self):
        out = blob.safe_filename("x" * 900 + ".ifc")
        assert out.endswith(".ifc")
        assert len(out.encode("utf-8")) <= 512


class TestSourceRef:
    def test_finds_the_upload_without_knowing_its_name(self):
        store = blob.FakeBlobStore()
        store.put(blob.source_key("dsn_1", "ward-a.ifc"), b"ISO-10303-21;")
        store.put(blob.glb_key("dsn_1", "mod_1"), b"")
        assert store.source_ref("dsn_1") == "designs/dsn_1/ward-a.ifc"

    def test_raises_when_there_is_no_source(self):
        with pytest.raises(LookupError):
            blob.FakeBlobStore().source_ref("dsn_missing")

    def test_raises_rather_than_guessing_between_two_sources(self):
        """'One source per design' isn't enforced by the bucket — if a replace
        flow or a partial retry ever leaves two, reading the first would silently
        return the wrong bytes."""
        store = blob.FakeBlobStore()
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.source_key("dsn_1", "b.ifc"), b"")
        with pytest.raises(LookupError):
            store.source_ref("dsn_1")


class TestDeletePrefix:
    def test_removes_the_source_and_every_glb(self):
        store = blob.FakeBlobStore()
        store.put(blob.source_key("dsn_1", "ward-a.ifc"), b"")
        store.put(blob.glb_key("dsn_1", "mod_1"), b"")
        store.put(blob.glb_key("dsn_1", "mod_2"), b"")
        assert store.delete_prefix(blob.design_prefix("dsn_1")) == 3

    def test_leaves_other_designs_alone(self):
        store = blob.FakeBlobStore()
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.source_key("dsn_2", "b.ifc"), b"")
        store.delete_prefix(blob.design_prefix("dsn_1"))
        assert store.source_ref("dsn_2") == "designs/dsn_2/b.ifc"

    def test_deleting_nothing_is_not_an_error(self):
        assert blob.FakeBlobStore().delete_prefix(blob.design_prefix("dsn_gone")) == 0


class TestGetBlobStore:
    def test_returns_a_store_with_the_interface(self):
        store = blob.get_blob_store()
        assert all(
            hasattr(store, m) for m in ("put", "url_for", "source_ref", "delete_prefix")
        )

    def test_is_a_singleton(self):
        """One store instance per process, so a spy set on it in one place is
        seen everywhere (and so a real client isn't rebuilt per request)."""
        assert blob.get_blob_store() is blob.get_blob_store()
