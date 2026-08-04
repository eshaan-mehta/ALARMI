"""Unit tests for the blob-storage seam (`app/blob.py`).

Uploaded IFC files and the GLBs the processor emits live in object storage
(Google Cloud Storage), not the database or local disk. Local dev and tests use
a *fake* store that keeps objects in process memory; Cloud Run uses the real
``GcsBlobStore``.

The important structure here is ``BlobStoreContract``: the behaviour every store
must exhibit, run against *both* implementations. The two answer the same
questions by different mechanisms — the fake filters a Python set, GCS relies on
list-prefix and delimiter semantics — so testing only the fake would let the
implementation that actually runs in production drift undetected.
"""

import pytest

from app import blob

# --------------------------------------------------------------------------
# Doubles for the slice of google.cloud.storage that GcsBlobStore touches.
# --------------------------------------------------------------------------


class _StubBlob:
    def __init__(self, bucket: "_StubBucket", name: str) -> None:
        self._bucket = bucket
        self.name = name

    def upload_from_string(self, data: bytes) -> None:
        self._bucket.objects[self.name] = data

    def download_as_bytes(self) -> bytes:
        # Real GCS raises google.cloud.exceptions.NotFound here; KeyError is the
        # closest thing available without importing the SDK.
        return self._bucket.objects[self.name]

    def delete(self) -> None:
        self._bucket.objects.pop(self.name, None)


class _StubBucket:
    """Models ``Bucket.list_blobs`` faithfully enough to catch logic errors.

    Real GCS has no directories — ``delimiter="/"`` makes it return only objects
    whose name *after the prefix* contains no further "/", rolling deeper ones up
    into ``prefixes`` instead of yielding them as blobs. That is exactly the
    behaviour ``GcsBlobStore.source_ref`` leans on to skip the ``modules/``
    subtree, so the stub reproduces it rather than hand-waving it.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.objects: dict[str, bytes] = {}

    def blob(self, name: str) -> _StubBlob:
        return _StubBlob(self, name)

    def list_blobs(self, prefix: str = "", delimiter: str | None = None):
        names = sorted(n for n in self.objects if n.startswith(prefix))
        if delimiter:
            names = [n for n in names if delimiter not in n[len(prefix) :]]
        # Real GCS hands back a lazy paged iterator, not a list.
        return iter([_StubBlob(self, n) for n in names])


class _StubGcsClient:
    def __init__(self) -> None:
        self._buckets: dict[str, _StubBucket] = {}

    def bucket(self, name: str) -> _StubBucket:
        return self._buckets.setdefault(name, _StubBucket(name))


class TestStubFidelity:
    """The contract suite below is only as good as the stub, so pin the one
    behaviour it exists to model."""

    def test_delimiter_hides_the_nested_subtree(self):
        bucket = _StubBucket("b")
        bucket.objects["designs/d1/ward.ifc"] = b""
        bucket.objects["designs/d1/modules/m1.glb"] = b""
        shallow = [b.name for b in bucket.list_blobs(prefix="designs/d1/", delimiter="/")]
        assert shallow == ["designs/d1/ward.ifc"]

    def test_without_a_delimiter_the_whole_subtree_comes_back(self):
        bucket = _StubBucket("b")
        bucket.objects["designs/d1/ward.ifc"] = b""
        bucket.objects["designs/d1/modules/m1.glb"] = b""
        assert len(list(bucket.list_blobs(prefix="designs/d1/"))) == 2

    def test_listing_is_scoped_to_the_prefix(self):
        bucket = _StubBucket("b")
        bucket.objects["designs/d1/a.ifc"] = b""
        bucket.objects["designs/d2/b.ifc"] = b""
        assert [b.name for b in bucket.list_blobs(prefix="designs/d1/")] == ["designs/d1/a.ifc"]


# --------------------------------------------------------------------------
# The contract — run against every implementation.
# --------------------------------------------------------------------------


class BlobStoreContract:
    """Behaviour the app depends on, regardless of which store is wired in.

    Not collected directly (no ``Test`` prefix); subclasses supply ``store``.
    """

    def test_a_stored_source_is_found_without_knowing_its_name(self, store):
        store.put(blob.source_key("dsn_1", "ward-a.ifc"), b"ISO-10303-21;")
        assert store.source_ref("dsn_1") == "designs/dsn_1/ward-a.ifc"

    def test_stored_bytes_come_back_byte_for_byte(self, store):
        """The processing worker reads back the IFC the upload handler wrote, so
        a store that only remembers keys isn't enough."""
        key = blob.source_key("dsn_1", "ward-a.ifc")
        store.put(key, b"ISO-10303-21;\nHEADER;\n\x00\xff binary tail")
        assert store.get(key) == b"ISO-10303-21;\nHEADER;\n\x00\xff binary tail"

    def test_a_rewritten_object_reads_back_as_the_new_bytes(self, store):
        key = blob.glb_key("dsn_1", "mod_1")
        store.put(key, b"glTF-old")
        store.put(key, b"glTF-new")
        assert store.get(key) == b"glTF-new"

    def test_reading_a_deleted_object_fails(self, store):
        key = blob.source_key("dsn_1", "ward-a.ifc")
        store.put(key, b"x")
        store.delete_prefix(blob.design_prefix("dsn_1"))
        with pytest.raises(Exception):  # noqa: B017 — KeyError / NotFound
            store.get(key)

    def test_module_glbs_are_not_mistaken_for_the_source(self, store):
        """GLBs live one level deeper, under modules/. The lookup must skip
        them however the store enumerates objects."""
        store.put(blob.source_key("dsn_1", "ward-a.ifc"), b"")
        for i in range(5):
            store.put(blob.glb_key("dsn_1", f"mod_{i}"), b"")
        assert store.source_ref("dsn_1") == "designs/dsn_1/ward-a.ifc"

    def test_the_lookup_is_scoped_to_one_design(self, store):
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.source_key("dsn_2", "b.ifc"), b"")
        assert store.source_ref("dsn_1") == "designs/dsn_1/a.ifc"
        assert store.source_ref("dsn_2") == "designs/dsn_2/b.ifc"

    def test_a_design_with_no_source_raises(self, store):
        with pytest.raises(LookupError):
            store.source_ref("dsn_missing")

    def test_two_sources_raise_rather_than_guess(self, store):
        """'One source per design' isn't enforced by the bucket. If a replace
        flow or a partial retry ever leaves two, picking the first would return
        the wrong bytes silently."""
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.source_key("dsn_1", "b.ifc"), b"")
        with pytest.raises(LookupError):
            store.source_ref("dsn_1")

    def test_a_design_with_only_glbs_has_no_source(self, store):
        store.put(blob.glb_key("dsn_1", "mod_1"), b"")
        with pytest.raises(LookupError):
            store.source_ref("dsn_1")

    def test_deleting_a_design_takes_its_source_and_every_glb(self, store):
        store.put(blob.source_key("dsn_1", "ward-a.ifc"), b"")
        store.put(blob.glb_key("dsn_1", "mod_1"), b"")
        store.put(blob.glb_key("dsn_1", "mod_2"), b"")
        assert store.delete_prefix(blob.design_prefix("dsn_1")) == 3
        with pytest.raises(LookupError):
            store.source_ref("dsn_1")

    def test_deleting_one_design_leaves_the_others_untouched(self, store):
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.glb_key("dsn_1", "mod_1"), b"")
        store.put(blob.source_key("dsn_2", "b.ifc"), b"")
        store.put(blob.glb_key("dsn_2", "mod_2"), b"")
        store.delete_prefix(blob.design_prefix("dsn_1"))
        assert store.source_ref("dsn_2") == "designs/dsn_2/b.ifc"
        assert store.delete_prefix(blob.design_prefix("dsn_2")) == 2

    def test_deleting_nothing_is_not_an_error(self, store):
        assert store.delete_prefix(blob.design_prefix("dsn_gone")) == 0

    def test_deleting_twice_is_idempotent(self, store):
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        prefix = blob.design_prefix("dsn_1")
        assert store.delete_prefix(prefix) == 1
        assert store.delete_prefix(prefix) == 0

    def test_a_design_id_that_prefixes_another_is_not_swept_up(self, store):
        """`designs/dsn_1/` must not match `designs/dsn_10/` — the trailing
        slash is what keeps sibling ids apart."""
        store.put(blob.source_key("dsn_1", "a.ifc"), b"")
        store.put(blob.source_key("dsn_10", "b.ifc"), b"")
        assert store.delete_prefix(blob.design_prefix("dsn_1")) == 1
        assert store.source_ref("dsn_10") == "designs/dsn_10/b.ifc"

    def test_a_filename_with_spaces_round_trips(self, store):
        store.put(blob.source_key("dsn_1", "Ward A Rev 2.ifc"), b"")
        assert store.source_ref("dsn_1") == "designs/dsn_1/Ward A Rev 2.ifc"


class TestFakeBlobStoreContract(BlobStoreContract):
    @pytest.fixture
    def store(self):
        return blob.FakeBlobStore()


class TestGcsBlobStoreContract(BlobStoreContract):
    """The implementation that actually runs on Cloud Run, driven by a stub
    client so the list/delete logic is exercised without credentials."""

    @pytest.fixture
    def store(self):
        return blob.GcsBlobStore("test-bucket", client=_StubGcsClient())


class TestGcsBlobStoreWiring:
    def test_put_lands_the_bytes_in_the_bucket(self):
        client = _StubGcsClient()
        store = blob.GcsBlobStore("test-bucket", client=client)
        store.put("designs/dsn_1/ward.ifc", b"ISO-10303-21;")
        assert client.bucket("test-bucket").objects["designs/dsn_1/ward.ifc"] == b"ISO-10303-21;"

    def test_delete_actually_removes_objects_not_just_counts_them(self):
        """delete_prefix returns a count; make sure the count isn't the only
        thing that happens."""
        client = _StubGcsClient()
        store = blob.GcsBlobStore("test-bucket", client=client)
        store.put(blob.source_key("dsn_1", "a.ifc"), b"x")
        store.put(blob.glb_key("dsn_1", "mod_1"), b"y")
        store.delete_prefix(blob.design_prefix("dsn_1"))
        assert client.bucket("test-bucket").objects == {}


# --------------------------------------------------------------------------
# Fake-only behaviour and pure helpers.
# --------------------------------------------------------------------------


class TestFakeBlobStore:
    def test_put_accepts_bytes_and_returns_nothing(self):
        assert blob.FakeBlobStore().put("designs/dsn_1/source.ifc", b"ISO-10303-21;") is None

    def test_put_takes_arbitrary_sizes(self):
        store = blob.FakeBlobStore()
        store.put("empty", b"")
        store.put("largeish", b"x" * 100_000)
        assert store.get("empty") == b""
        assert store.get("largeish") == b"x" * 100_000

    def test_getting_an_unknown_key_raises(self):
        with pytest.raises(KeyError):
            blob.FakeBlobStore().get("designs/dsn_1/never-written.ifc")

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
    """The key layout is itself a requirement — the bucket listing is meant to
    read like the user's uploads — so these pin the shape deliberately."""

    def test_source_key_keeps_the_uploaded_filename(self):
        assert blob.source_key("dsn_1", "ward-a.ifc") == "designs/dsn_1/ward-a.ifc"

    def test_glb_key_is_nested_under_its_design(self):
        assert blob.glb_key("dsn_1", "mod_1") == "designs/dsn_1/modules/mod_1.glb"

    def test_same_filename_in_two_designs_does_not_collide(self):
        """Uniqueness comes from the design id, not the name."""
        assert blob.source_key("dsn_1", "model.ifc") != blob.source_key("dsn_2", "model.ifc")


class TestSafeFilename:
    """Only the inputs that can't reach the server through an HTTP upload live
    here — the rest are asserted end to end in test_upload_api.py."""

    def test_a_windows_path_is_reduced_to_its_last_segment(self):
        """Not testable through the endpoint: the HTTP client strips a
        backslash path out of the multipart filename before it is sent, so an
        API-level assertion would be exercising httpx, not this function. A
        non-browser client can still put one on the wire.
        """
        assert blob.safe_filename(r"C:\models\ward.ifc") == "ward.ifc"

    def test_control_characters_are_dropped(self):
        assert blob.safe_filename("wa\x00rd\x1f.ifc") == "ward.ifc"

    def test_absurd_names_are_truncated_but_keep_the_extension(self):
        out = blob.safe_filename("x" * 900 + ".ifc")
        assert out.endswith(".ifc")
        assert len(out.encode("utf-8")) <= 512

    def test_a_truncated_name_is_still_valid_utf8(self):
        """Truncation is by bytes, so it must not slice a multi-byte character
        in half — GCS object names have to be valid UTF-8."""
        out = blob.safe_filename("é" * 400 + ".ifc")
        out.encode("utf-8").decode("utf-8")  # raises if the cut was mid-character


class TestGetBlobStore:
    def test_the_configured_store_round_trips_a_design(self):
        """Behavioural stand-in for 'implements the interface': put a source,
        find it, delete it."""
        store = blob.get_blob_store()
        store.put(blob.source_key("dsn_probe", "probe.ifc"), b"x")
        assert store.source_ref("dsn_probe") == "designs/dsn_probe/probe.ifc"
        assert store.delete_prefix(blob.design_prefix("dsn_probe")) == 1

    def test_is_a_singleton(self):
        """One store instance per process, so a spy set on it in one place is
        seen everywhere (and so a real client isn't rebuilt per request)."""
        assert blob.get_blob_store() is blob.get_blob_store()
