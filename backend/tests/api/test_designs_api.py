"""Endpoint tests for reading, renaming, deleting and tracking a design.

Sources of truth:
  * FS2 — the interface must show processing status (complete / processing / failed)
  * FS3 — a user can view, rename and delete uploaded files
  * design doc Table 4 — `GET /api/files/{fileId}/status`
  * `website/src/data/designs/api.ts` + `hooks.ts` — the dashboard lists a
    project's designs (metadata only), polls status, lazily fetches modules,
    renames via `PATCH {name}` and deletes via `DELETE`
"""

import pytest

from conftest import DESIGN_FIELDS, MODULE_FIELDS, STATUSES, UNIT_SCALES


class TestListProjectDesigns:
    def test_empty_project_returns_an_empty_list(self, client, project):
        res = client.get(f"/api/projects/{project['projectId']}/designs")
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_the_exact_client_shape(self, client, project, upload_design):
        upload_design(project["projectId"])
        body = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert set(body[0]) == DESIGN_FIELDS

    def test_ships_metadata_only(self, client, project, upload_design):
        """Lazy loading: modules are a separate request, never inlined here."""
        upload_design(project["projectId"])
        body = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert "modules" not in body[0]

    def test_newest_first(self, client, project, upload_design):
        first = upload_design(project["projectId"], name="First", filename="a.ifc")
        second = upload_design(project["projectId"], name="Second", filename="b.ifc")
        ids = [d["designId"] for d in client.get(f"/api/projects/{project['projectId']}/designs").json()]
        assert ids == [second["designId"], first["designId"]]

    def test_scoped_to_the_project(self, client, make_project, upload_design):
        mine = make_project(name="Mine")
        theirs = make_project(name="Theirs")
        upload_design(mine["projectId"], name="Mine's design")
        upload_design(theirs["projectId"], name="Theirs' design")
        body = client.get(f"/api/projects/{mine['projectId']}/designs").json()
        assert [d["name"] for d in body] == ["Mine's design"]

    def test_unknown_project_is_404(self, client):
        """A stale or hand-typed project URL must read as "not found", not as an
        empty project — the dashboard can't tell the difference otherwise."""
        res = client.get("/api/projects/prj_missing/designs")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_module_count_matches_the_modules_endpoint(self, client, project, upload_design):
        created = upload_design(project["projectId"])
        listed = client.get(f"/api/projects/{project['projectId']}/designs").json()[0]
        modules = client.get(f"/api/designs/{created['designId']}/modules").json()
        assert listed["moduleCount"] == len(modules)


class TestGetDesign:
    def test_returns_the_design(self, client, design):
        res = client.get(f"/api/designs/{design['designId']}")
        assert res.status_code == 200
        assert res.json() == design

    def test_unknown_design_is_404(self, client):
        res = client.get("/api/designs/dsn_missing")
        assert res.status_code == 404
        assert res.json()["message"]


class TestDesignStatus:
    def test_returns_a_status_the_client_renders(self, client, design):
        """FS2 — the badge only knows PROCESSING / COMPLETE / ERROR."""
        res = client.get(f"/api/designs/{design['designId']}/status")
        assert res.status_code == 200
        assert res.json()["status"] in STATUSES

    def test_agrees_with_the_design_body(self, client, design):
        status = client.get(f"/api/designs/{design['designId']}/status").json()["status"]
        assert status == client.get(f"/api/designs/{design['designId']}").json()["status"]

    def test_unknown_design_is_404(self, client):
        res = client.get("/api/designs/dsn_missing/status")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_is_cheap_to_poll(self, client, design):
        """The dashboard polls this every 2s while anything is processing."""
        for _ in range(5):
            assert client.get(f"/api/designs/{design['designId']}/status").status_code == 200


class TestDesignModules:
    def test_returns_the_extracted_modules(self, client, design):
        res = client.get(f"/api/designs/{design['designId']}/modules")
        assert res.status_code == 200
        assert len(res.json()) == design["moduleCount"]

    def test_returns_the_exact_client_shape(self, client, design):
        body = client.get(f"/api/designs/{design['designId']}/modules").json()
        assert set(body[0]) == MODULE_FIELDS

    def test_metadata_is_displayable(self, client, design):
        """Table 5 fields the panel renders: type, dimensions, room, unit."""
        for module in client.get(f"/api/designs/{design['designId']}/modules").json():
            assert module["moduleId"]
            assert module["type"]
            assert module["roomId"]
            assert module["unitScale"] in UNIT_SCALES
            assert set(module["dimensions"]) == {"x", "y", "z"}
            assert all(v > 0 for v in module["dimensions"].values())

    def test_unknown_design_is_404(self, client):
        res = client.get("/api/designs/dsn_missing/modules")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_order_is_stable(self, client, design):
        """The panel is a list the user reads; rows must not shuffle between
        expands."""
        first = [m["moduleId"] for m in client.get(f"/api/designs/{design['designId']}/modules").json()]
        second = [m["moduleId"] for m in client.get(f"/api/designs/{design['designId']}/modules").json()]
        assert first == second

    def test_scoped_to_one_design(self, client, project, upload_design):
        one = upload_design(project["projectId"], filename="one.ifc")
        two = upload_design(project["projectId"], filename="two.ifc")
        ids_one = {m["moduleId"] for m in client.get(f"/api/designs/{one['designId']}/modules").json()}
        ids_two = {m["moduleId"] for m in client.get(f"/api/designs/{two['designId']}/modules").json()}
        assert ids_one.isdisjoint(ids_two)


class TestRenameDesign:
    def test_renames(self, client, design):
        res = client.patch(f"/api/designs/{design['designId']}", json={"name": "Renamed"})
        assert res.status_code == 200
        assert res.json()["name"] == "Renamed"

    def test_persists(self, client, design):
        client.patch(f"/api/designs/{design['designId']}", json={"name": "Renamed"})
        assert client.get(f"/api/designs/{design['designId']}").json()["name"] == "Renamed"

    def test_trims_whitespace(self, client, design):
        res = client.patch(f"/api/designs/{design['designId']}", json={"name": "  Padded  "})
        assert res.json()["name"] == "Padded"

    def test_keeps_the_upload_facts_and_modules(self, client, design):
        res = client.patch(f"/api/designs/{design['designId']}", json={"name": "Renamed"}).json()
        assert res["designId"] == design["designId"]
        assert res["fileName"] == design["fileName"]
        assert res["fileSize"] == design["fileSize"]
        assert res["uploadTime"] == design["uploadTime"]
        assert res["moduleCount"] == design["moduleCount"]

    @pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {"name": None}])
    def test_rejects_a_blank_name(self, client, design, body):
        res = client.patch(f"/api/designs/{design['designId']}", json=body)
        assert res.status_code == 400
        assert res.json()["message"]

    def test_unknown_design_is_404(self, client):
        res = client.patch("/api/designs/dsn_missing", json={"name": "Renamed"})
        assert res.status_code == 404
        assert res.json()["message"]

    def test_cannot_rewrite_server_owned_fields(self, client, design):
        """FS3 is rename-only: status, file facts and parentage are not the
        client's to set."""
        res = client.patch(
            f"/api/designs/{design['designId']}",
            json={
                "name": "Renamed",
                "status": "ERROR",
                "fileName": "hacked.ifc",
                "fileSize": 1,
                "projectId": "prj_elsewhere",
                "moduleCount": 999,
            },
        )
        assert res.status_code in (200, 400)
        current = client.get(f"/api/designs/{design['designId']}").json()
        assert current["status"] == design["status"]
        assert current["fileName"] == design["fileName"]
        assert current["fileSize"] == design["fileSize"]
        assert current["projectId"] == design["projectId"]
        assert current["moduleCount"] == design["moduleCount"]


class TestDeleteDesign:
    def test_returns_204_with_no_body(self, client, design):
        res = client.delete(f"/api/designs/{design['designId']}")
        assert res.status_code == 204
        assert res.content == b""

    def test_the_design_is_gone(self, client, design):
        client.delete(f"/api/designs/{design['designId']}")
        assert client.get(f"/api/designs/{design['designId']}").status_code == 404

    def test_disappears_from_the_project_list(self, client, project, upload_design):
        created = upload_design(project["projectId"])
        client.delete(f"/api/designs/{created['designId']}")
        assert client.get(f"/api/projects/{project['projectId']}/designs").json() == []

    def test_decrements_the_projects_design_count(self, client, project, upload_design):
        created = upload_design(project["projectId"])
        client.delete(f"/api/designs/{created['designId']}")
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 0

    def test_takes_its_modules_with_it(self, client, design):
        module_ids = [m["moduleId"] for m in client.get(f"/api/designs/{design['designId']}/modules").json()]
        client.delete(f"/api/designs/{design['designId']}")
        assert client.get(f"/api/designs/{design['designId']}/modules").status_code == 404
        for module_id in module_ids:
            assert client.patch(f"/api/modules/{module_id}", json={"type": "X"}).status_code == 404

    def test_takes_its_blobs_with_it(self, client, design):
        """Deleting a design used to leave its source IFC and every module GLB
        orphaned in the bucket forever — nothing ever removed them."""
        from app import blob

        store = blob.get_blob_store()
        prefix = blob.design_prefix(design["designId"])
        assert store.source_ref(design["designId"]).startswith(prefix)
        client.delete(f"/api/designs/{design['designId']}")
        with pytest.raises(LookupError):
            store.source_ref(design["designId"])
        assert store.delete_prefix(prefix) == 0  # nothing left under the prefix

    def test_blob_cleanup_failure_still_deletes_the_design(self, client, design, monkeypatch):
        """Storage is best-effort on the way out: the row is already gone, so a
        failed wipe leaves orphans (recoverable) rather than a failed request."""
        from app import blob

        def _boom(_prefix):
            raise RuntimeError("gcs down")

        monkeypatch.setattr(blob.get_blob_store(), "delete_prefix", _boom)
        assert client.delete(f"/api/designs/{design['designId']}").status_code == 204
        assert client.get(f"/api/designs/{design['designId']}").status_code == 404

    def test_leaves_another_designs_blobs_alone(self, client, project, upload_design):
        from app import blob

        store = blob.get_blob_store()
        keep = upload_design(project["projectId"], name="Keep", filename="keep.ifc")
        drop = upload_design(project["projectId"], name="Drop", filename="drop.ifc")
        client.delete(f"/api/designs/{drop['designId']}")
        assert store.source_ref(keep["designId"]).endswith("/keep.ifc")

    def test_deleting_twice_is_404(self, client, design):
        client.delete(f"/api/designs/{design['designId']}")
        res = client.delete(f"/api/designs/{design['designId']}")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_unknown_design_is_404(self, client):
        res = client.delete("/api/designs/dsn_missing")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_leaves_sibling_designs_intact(self, client, project, upload_design):
        keep = upload_design(project["projectId"], name="Keep", filename="keep.ifc")
        drop = upload_design(project["projectId"], name="Drop", filename="drop.ifc")
        client.delete(f"/api/designs/{drop['designId']}")
        assert client.get(f"/api/designs/{keep['designId']}").status_code == 200
        modules = client.get(f"/api/designs/{keep['designId']}/modules").json()
        assert len(modules) == keep["moduleCount"]
