"""Spec surface the backend must eventually serve but Phase 1 deliberately does not.

Everything here is `xfail`: it documents a requirement from the design document
that the current slice hasn't implemented, so the gap stays visible and the test
flips to a pass (XPASS) the moment the slice lands. Nothing here is a regression.

Run just this file to see the outstanding spec surface:

    uv run pytest tests/spec -rxX
"""

import time

import pytest

from conftest import ifc_bytes

pytestmark = pytest.mark.deferred


def _project_with_design(client):
    project = client.post(
        "/api/projects", json={"name": "Spec Project", "location": "Portland, OR"}
    ).json()
    design = client.post(
        f"/api/projects/{project['projectId']}/designs",
        data={"name": "Spec design"},
        files={"file": ("spec.ifc", ifc_bytes(2048), "application/octet-stream")},
    ).json()
    return project, design


class TestMobileEndpoints:
    """Design doc Table 4 — the endpoints the mobile app subsystem calls
    (§3.3.1). None are mounted yet; the web contract came first."""

    @pytest.mark.xfail(reason="Table 4 GET /api/modules/all_metadata not implemented", strict=False)
    def test_all_module_metadata(self, client):
        _project_with_design(client)
        res = client.get("/api/modules/all_metadata")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    @pytest.mark.xfail(reason="Table 4 GET /api/modules/{moduleId} not implemented", strict=False)
    def test_get_one_module(self, client):
        _, design = _project_with_design(client)
        module_id = client.get(f"/api/designs/{design['designId']}/modules").json()[0]["moduleId"]
        res = client.get(f"/api/modules/{module_id}")
        assert res.status_code == 200
        assert res.json()["moduleId"] == module_id

    @pytest.mark.xfail(reason="Table 4 GET /api/modules/project_modules/{project} not implemented", strict=False)
    def test_modules_for_a_project(self, client):
        """The mobile module browser lists every module in a project, across all
        of that project's uploaded designs."""
        project, design = _project_with_design(client)
        expected = client.get(f"/api/designs/{design['designId']}/modules").json()
        res = client.get(f"/api/modules/project_modules/{project['projectId']}")
        assert res.status_code == 200
        assert {m["moduleId"] for m in res.json()} == {m["moduleId"] for m in expected}

    @pytest.mark.xfail(reason="Table 4 DELETE /api/modules/{moduleId} not implemented", strict=False)
    def test_delete_a_module(self, client):
        _, design = _project_with_design(client)
        modules = client.get(f"/api/designs/{design['designId']}/modules").json()
        res = client.delete(f"/api/modules/{modules[0]['moduleId']}")
        assert res.status_code in (200, 204)
        remaining = client.get(f"/api/designs/{design['designId']}/modules").json()
        assert len(remaining) == len(modules) - 1

    @pytest.mark.xfail(reason="Blob storage + GLB conversion deferred (FS4)", strict=False)
    def test_presigned_glb_url(self, client):
        """Table 4 + §3.2.4: the GLB is stored in blob storage under the
        ModuleID, and the API hands back a presigned URL for it."""
        _, design = _project_with_design(client)
        module_id = client.get(f"/api/designs/{design['designId']}/modules").json()[0]["moduleId"]
        res = client.get(f"/api/objects/get_url/{module_id}")
        assert res.status_code == 200
        assert res.json()["url"].startswith("http")


class TestRealProcessing:
    """FS4/FS5 + §3.2.3 — the processor is a stub today: it fabricates modules
    from the file size and never opens the file."""

    @pytest.mark.xfail(reason="Uploaded IFC bytes are discarded — no blob storage yet (FS4)", strict=False)
    def test_the_uploaded_file_is_retained(self, client):
        _, design = _project_with_design(client)
        res = client.get(f"/api/designs/{design['designId']}/file")
        assert res.status_code == 200
        assert res.content.startswith(b"ISO-10303-21;")

    @pytest.mark.xfail(reason="Stub processor fabricates modules from file size", strict=False)
    def test_a_file_with_no_marked_modules_yields_no_modules(self, client):
        """§3.2.3: modules come from elements carrying
        `FloorMark.IsMarkingModule`. A file with none must extract none."""
        project = client.post(
            "/api/projects", json={"name": "Empty IFC", "location": "X"}
        ).json()
        design = client.post(
            f"/api/projects/{project['projectId']}/designs",
            data={"name": "No modules"},
            files={"file": ("empty.ifc", ifc_bytes(2048), "application/octet-stream")},
        ).json()
        assert design["moduleCount"] == 0
        assert client.get(f"/api/designs/{design['designId']}/modules").json() == []

    @pytest.mark.xfail(reason="Stub processor does not parse the file", strict=False)
    def test_module_ids_come_from_the_ifc_global_ids(self, client):
        """Table 5: ModuleID is `IfcElement.GlobalId` (22-char IFC GUID), not a
        server-minted id — the mobile app and the authoring tool have to agree
        on the same identifier."""
        _, design = _project_with_design(client)
        modules = client.get(f"/api/designs/{design['designId']}/modules").json()
        assert all(len(m["moduleId"]) == 22 for m in modules)

    @pytest.mark.xfail(reason="Boundary polygon / pose / marks / origin not stored yet", strict=False)
    def test_the_full_table_5_metadata_is_stored(self, client):
        """Table 6's Module row carries more than the web panel shows: the
        boundary polygon and origin the robot marks, and the pose and marks the
        mobile app places."""
        _, design = _project_with_design(client)
        module = client.get(f"/api/designs/{design['designId']}/modules").json()[0]
        assert {"pose", "marks", "boundaryPolygon", "roomOrigin"} <= set(module)

    @pytest.mark.xfail(reason="Processing is synchronous, so a design is never observably PROCESSING", strict=False)
    def test_processing_is_asynchronous(self, client):
        """FS2 only means something if the user can see the in-progress state;
        NFS8 allows up to 2 minutes for a 50 MB file, which cannot block the
        upload response."""
        project = client.post("/api/projects", json={"name": "Async", "location": "X"}).json()
        res = client.post(
            f"/api/projects/{project['projectId']}/designs",
            data={"name": "Async design"},
            files={"file": ("async.ifc", ifc_bytes(4096), "application/octet-stream")},
        )
        assert res.json()["status"] == "PROCESSING"

    @pytest.mark.xfail(reason="No failure path — the stub always succeeds", strict=False)
    def test_an_unparseable_file_ends_in_error(self, client):
        """FS2 lists "failed" as a status the user must see."""
        project = client.post("/api/projects", json={"name": "Bad", "location": "X"}).json()
        design = client.post(
            f"/api/projects/{project['projectId']}/designs",
            data={"name": "Corrupt"},
            files={"file": ("corrupt.ifc", b"this is not an IFC file", "application/octet-stream")},
        ).json()
        deadline = time.monotonic() + 5
        status = design["status"]
        while status == "PROCESSING" and time.monotonic() < deadline:
            status = client.get(f"/api/designs/{design['designId']}/status").json()["status"]
        assert status == "ERROR"


class TestOperationalGaps:
    @pytest.mark.xfail(reason="Oversize uploads are buffered to disk before the size check", strict=False)
    def test_an_oversize_upload_is_rejected_before_it_is_buffered(self, client, monkeypatch):
        """NFS12 caps uploads at 1 GB, but the cap is checked only after
        Starlette has spooled the whole body. The `Content-Length` header should
        be refused up front so a 5 GB POST can't fill the disk."""
        from app.designs import router as designs_router

        monkeypatch.setattr(designs_router, "_ONE_GB", 512)
        project = client.post("/api/projects", json={"name": "Big", "location": "X"}).json()
        res = client.post(
            f"/api/projects/{project['projectId']}/designs",
            data={"name": "Huge"},
            files={"file": ("huge.ifc", ifc_bytes(4096), "application/octet-stream")},
            headers={"X-Expect-Early-Rejection": "1"},
        )
        assert res.status_code == 413

    @pytest.mark.xfail(reason="No pagination — the dashboard fetches every row", strict=False)
    def test_project_designs_are_pageable(self, client):
        project = client.post("/api/projects", json={"name": "Paged", "location": "X"}).json()
        for i in range(3):
            client.post(
                f"/api/projects/{project['projectId']}/designs",
                data={"name": f"D{i}"},
                files={"file": (f"d{i}.ifc", ifc_bytes(300 + i), "application/octet-stream")},
            )
        res = client.get(f"/api/projects/{project['projectId']}/designs", params={"limit": 2})
        assert len(res.json()) == 2

    @pytest.mark.xfail(reason="No auth — every caller is anonymous", strict=False)
    def test_the_api_requires_a_caller_identity(self, client):
        """Deferred by plan, but worth keeping visible: today anyone who can
        reach the host can delete any design."""
        res = client.get("/api/projects/all_projects", headers={})
        assert res.status_code == 401
