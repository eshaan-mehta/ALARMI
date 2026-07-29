"""Endpoint tests for uploading a design.

`POST /api/projects/{projectId}/designs` — multipart { name, file }.

Sources of truth:
  * FS1 — must accept an IFC upload and confirm success
  * NFS12 — must support IFC files up to 1 GB
  * design doc Table 4 — Files POST, project in the path, file in the body
  * `website/src/data/designs/api.ts::uploadDesign` and `UploadModal.tsx` — the
    client sends `name` + `file` as form fields and shows `data.message` on error
"""

import pytest

from app.designs import router as designs_router
from conftest import DESIGN_FIELDS, MIN_IFC_SIZE, STATUSES, ifc_bytes


def _post(client, project_id, *, name="Ward A Headwall", filename="ward-a.ifc", content=None):
    files = None
    if content is not None or filename is not None:
        files = {"file": (filename, content if content is not None else ifc_bytes(), "application/octet-stream")}
    return client.post(
        f"/api/projects/{project_id}/designs", data={"name": name}, files=files
    )


class TestSuccessfulUpload:
    def test_returns_201_and_the_created_design(self, client, project):
        res = _post(client, project["projectId"])
        assert res.status_code == 201
        body = res.json()
        assert set(body) == DESIGN_FIELDS
        assert body["designId"]
        assert body["projectId"] == project["projectId"]
        assert body["name"] == "Ward A Headwall"
        assert body["fileName"] == "ward-a.ifc"
        assert body["status"] in STATUSES

    def test_records_the_real_byte_count(self, client, project):
        payload = ifc_bytes(MIN_IFC_SIZE + 500)
        res = _post(client, project["projectId"], content=payload)
        assert res.json()["fileSize"] == len(payload)

    def test_trims_the_name(self, client, project):
        res = _post(client, project["projectId"], name="  Ward A  ")
        assert res.json()["name"] == "Ward A"

    def test_falls_back_to_the_file_name_when_no_name_is_given(self, client, project):
        res = _post(client, project["projectId"], name="")
        assert res.json()["name"] == "ward-a.ifc"

    def test_accepts_an_uppercase_extension(self, client, project):
        """Windows-authored files often arrive as `.IFC`."""
        res = _post(client, project["projectId"], filename="WARD-A.IFC")
        assert res.status_code == 201

    def test_shows_up_in_the_projects_design_list(self, client, project):
        created = _post(client, project["projectId"]).json()
        designs = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert [d["designId"] for d in designs] == [created["designId"]]

    def test_increments_the_projects_design_count(self, client, project):
        _post(client, project["projectId"])
        listed = client.get("/api/projects/all_projects").json()
        assert listed[0]["designCount"] == 1

    def test_two_uploads_get_distinct_ids(self, client, project):
        one = _post(client, project["projectId"]).json()
        two = _post(client, project["projectId"]).json()
        assert one["designId"] != two["designId"]

    def test_the_same_name_twice_is_allowed(self, client, project):
        """Designs are identified by id; a repeat upload of a revision is normal."""
        assert _post(client, project["projectId"], name="Ward A").status_code == 201
        assert _post(client, project["projectId"], name="Ward A").status_code == 201

    def test_extracts_metadata_for_the_upload(self, client, project):
        """FS5: processing must store the module metadata, and it must be
        reachable through the modules endpoint once the design settles."""
        created = _post(client, project["projectId"]).json()
        settled = client.get(f"/api/designs/{created['designId']}").json()
        modules = client.get(f"/api/designs/{created['designId']}/modules").json()
        assert len(modules) == settled["moduleCount"] >= 1


class TestAsyncProcessing:
    """FS2/NFS8: extraction can take up to two minutes, so the upload can't block
    on it. It returns immediately in PROCESSING and a background worker settles
    the design to COMPLETE."""

    def test_upload_returns_processing_immediately(self, client, project):
        res = _post(client, project["projectId"])
        assert res.status_code == 201
        assert res.json()["status"] == "PROCESSING"
        assert res.json()["moduleCount"] == 0

    def test_processing_settles_to_complete(self, client, project):
        created = _post(client, project["projectId"]).json()
        status = client.get(f"/api/designs/{created['designId']}/status").json()["status"]
        assert status == "COMPLETE"

    def test_the_source_is_handed_to_blob_storage(self, client, project, monkeypatch):
        """The uploaded bytes are written to object storage under the design's
        source key (the fake store drops them; a real one keeps them)."""
        from app import blob

        put_keys: list[str] = []
        monkeypatch.setattr(blob.get_blob_store(), "put", lambda key, data: put_keys.append(key))
        created = _post(client, project["projectId"]).json()
        assert blob.source_key(created["designId"]) in put_keys


class TestUploadValidation:
    def test_unknown_project_is_404(self, client):
        res = _post(client, "prj_missing")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_a_missing_file_is_400(self, client, project):
        res = client.post(
            f"/api/projects/{project['projectId']}/designs", data={"name": "Ward A"}
        )
        assert res.status_code == 400
        assert res.json()["message"]

    @pytest.mark.parametrize("filename", ["model.step", "model.pdf", "model", "model.ifc.txt", "ifc"])
    def test_any_file_type_is_accepted(self, client, project, filename):
        """Uploads are no longer gated by extension — any document is accepted."""
        res = _post(client, project["projectId"], filename=filename)
        assert res.status_code == 201

    @pytest.mark.policy
    def test_an_empty_file_is_400(self, client, project):
        """A zero-byte upload can never yield modules — rejecting it up front
        beats a design that sits there with no metadata."""
        res = _post(client, project["projectId"], content=b"")
        assert res.status_code == 400
        assert res.json()["message"]

    def test_a_file_over_the_limit_is_400(self, client, project, monkeypatch):
        """NFS12 caps uploads at 1 GB. The limit is shrunk here so the test
        doesn't have to move a gigabyte."""
        monkeypatch.setattr(designs_router, "_ONE_GB", MIN_IFC_SIZE + 10)
        res = _post(client, project["projectId"], content=ifc_bytes(MIN_IFC_SIZE + 50))
        assert res.status_code == 400
        assert res.json()["message"]

    def test_a_file_at_the_limit_is_accepted(self, client, project, monkeypatch):
        """NFS12 says *up to* 1 GB — the boundary itself must work."""
        limit = MIN_IFC_SIZE + 100
        monkeypatch.setattr(designs_router, "_ONE_GB", limit)
        res = _post(client, project["projectId"], content=ifc_bytes(limit))
        assert res.status_code == 201

    def test_a_rejected_upload_creates_nothing(self, client, project):
        _post(client, project["projectId"], content=b"")  # empty file → 400
        assert client.get(f"/api/projects/{project['projectId']}/designs").json() == []
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 0

    def test_rejected_uploads_do_not_leak_modules(self, client, project):
        """A failed upload must not leave fabricated metadata behind."""
        _post(client, project["projectId"], content=b"")  # empty file → 400
        _post(client, "prj_missing")
        designs = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert designs == []
