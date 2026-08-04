"""Endpoint tests for the Projects resource.

Sources of truth:
  * design doc Table 4 — `GET /api/projects/all_projects`,
    `PATCH /api/projects/{...}` (rename, `new_name` in the body)
  * design doc Table 6 — a Project is (ProjectID PK, Name, Location)
  * `website/src/data/projects/api.ts` + `types.ts` — the exact request and
    response shapes the dashboard sends and consumes
"""

from datetime import datetime

import pytest

from app.db import SessionLocal
from app.modules.models import Module
from app.projects import repository as projects_repo
from conftest import PROJECT_FIELDS


def _attach_module(design_id: str, module_id: str) -> None:
    """Give a design a module without going through extraction, so tests about
    what a delete removes don't inherit whatever the processor happens to emit."""
    with SessionLocal() as session:
        session.add(Module(module_id=module_id, design_id=design_id, type="HEADWALL"))
        session.commit()


class TestListProjects:
    def test_returns_an_empty_list_when_there_is_nothing(self, client):
        res = client.get("/api/projects/all_projects")
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_the_exact_client_shape(self, client, make_project):
        make_project()
        body = client.get("/api/projects/all_projects").json()
        assert set(body[0]) == PROJECT_FIELDS

    def test_newest_first(self, client, make_project):
        first = make_project(name="First")
        second = make_project(name="Second")
        ids = [p["projectId"] for p in client.get("/api/projects/all_projects").json()]
        assert ids == [second["projectId"], first["projectId"]]

    def test_design_count_tracks_uploads(self, client, make_project, upload_design):
        project = make_project()
        upload_design(project["projectId"])
        body = client.get("/api/projects/all_projects").json()
        assert body[0]["designCount"] == 1

    def test_content_type_is_json(self, client):
        res = client.get("/api/projects/all_projects")
        assert res.headers["content-type"].startswith("application/json")


class TestCreateProject:
    def test_creates_and_returns_201(self, client):
        res = client.post(
            "/api/projects", json={"name": "Riverside Clinic", "location": "Portland, OR"}
        )
        assert res.status_code == 201
        body = res.json()
        assert set(body) == PROJECT_FIELDS
        assert body["name"] == "Riverside Clinic"
        assert body["location"] == "Portland, OR"
        assert body["designCount"] == 0
        assert body["projectId"]
        assert datetime.fromisoformat(body["createdTime"]).tzinfo is not None

    def test_appears_in_the_list_afterwards(self, client, make_project):
        created = make_project()
        ids = [p["projectId"] for p in client.get("/api/projects/all_projects").json()]
        assert created["projectId"] in ids

    def test_trims_whitespace(self, client):
        res = client.post(
            "/api/projects", json={"name": "  Clinic  ", "location": "  Portland  "}
        )
        assert res.json()["name"] == "Clinic"
        assert res.json()["location"] == "Portland"

    @pytest.mark.parametrize("body", [{}, {"location": "Portland"}, {"name": "", "location": "P"}, {"name": "   ", "location": "P"}])
    def test_rejects_a_missing_or_blank_name(self, client, body):
        res = client.post("/api/projects", json=body)
        assert res.status_code == 400
        assert res.json()["message"]

    @pytest.mark.parametrize("body", [{"name": "Clinic"}, {"name": "Clinic", "location": ""}, {"name": "Clinic", "location": "  "}])
    def test_rejects_a_missing_or_blank_location(self, client, body):
        """Table 6 makes Location part of a Project, and the create modal
        collects it."""
        res = client.post("/api/projects", json=body)
        assert res.status_code == 400
        assert res.json()["message"]

    def test_rejects_a_duplicate_name_with_409(self, client, make_project):
        make_project(name="Riverside Clinic")
        res = client.post(
            "/api/projects", json={"name": "Riverside Clinic", "location": "Elsewhere"}
        )
        assert res.status_code == 409
        assert res.json()["message"]

    @pytest.mark.policy
    @pytest.mark.parametrize("dupe", ["riverside clinic", "RIVERSIDE CLINIC", "  Riverside Clinic  "])
    def test_duplicate_detection_ignores_case_and_padding(self, client, make_project, dupe):
        make_project(name="Riverside Clinic")
        res = client.post("/api/projects", json={"name": dupe, "location": "Elsewhere"})
        assert res.status_code == 409

    def test_a_lost_race_is_still_a_409_not_a_500(self, client, make_project, monkeypatch):
        """Two dashboards creating the same name at once must not surface a
        server error: the unique constraint has to be handled, not just the
        check-then-insert."""
        make_project(name="Riverside Clinic")
        monkeypatch.setattr(projects_repo, "project_name_exists", lambda db, name: False)
        res = client.post(
            "/api/projects", json={"name": "Riverside Clinic", "location": "Elsewhere"}
        )
        assert res.status_code == 409
        assert res.json()["message"]

    def test_does_not_create_anything_when_rejected(self, client):
        client.post("/api/projects", json={"name": "", "location": ""})
        assert client.get("/api/projects/all_projects").json() == []


class TestRenameProject:
    def test_renames_and_returns_the_updated_project(self, client, make_project):
        project = make_project(name="Old Name")
        res = client.patch(
            f"/api/projects/{project['projectId']}", json={"new_name": "New Name"}
        )
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    def test_keeps_the_id_stable(self, client, make_project):
        """Identity is the id — a rename must not mint a new one."""
        project = make_project(name="Old Name")
        res = client.patch(
            f"/api/projects/{project['projectId']}", json={"new_name": "New Name"}
        )
        assert res.json()["projectId"] == project["projectId"]
        assert res.json()["createdTime"] == project["createdTime"]
        assert res.json()["location"] == project["location"]

    def test_keeps_the_designs_attached(self, client, make_project, upload_design):
        project = make_project()
        upload_design(project["projectId"])
        res = client.patch(
            f"/api/projects/{project['projectId']}", json={"new_name": "Renamed"}
        )
        assert res.json()["designCount"] == 1
        designs = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert len(designs) == 1

    def test_trims_whitespace(self, client, make_project):
        project = make_project()
        res = client.patch(
            f"/api/projects/{project['projectId']}", json={"new_name": "  Padded  "}
        )
        assert res.json()["name"] == "Padded"

    @pytest.mark.parametrize("body", [{}, {"new_name": ""}, {"new_name": "   "}])
    def test_rejects_a_missing_or_blank_name(self, client, make_project, body):
        project = make_project()
        res = client.patch(f"/api/projects/{project['projectId']}", json=body)
        assert res.status_code == 400
        assert res.json()["message"]

    def test_unknown_project_is_404(self, client):
        res = client.patch("/api/projects/prj_missing", json={"new_name": "New"})
        assert res.status_code == 404
        assert res.json()["message"]

    def test_renaming_onto_another_project_is_409(self, client, make_project):
        """Names are unique — the rename path has to enforce the same rule the
        create path does, not fall through to a database error."""
        make_project(name="Riverside Clinic")
        other = make_project(name="Bay St. Office")
        res = client.patch(
            f"/api/projects/{other['projectId']}", json={"new_name": "Riverside Clinic"}
        )
        assert res.status_code == 409
        assert res.json()["message"]

    def test_renaming_to_its_own_current_name_succeeds(self, client, make_project):
        """The modal is pre-filled with the current name; submitting unchanged
        is a no-op, not a conflict."""
        project = make_project(name="Riverside Clinic")
        res = client.patch(
            f"/api/projects/{project['projectId']}", json={"new_name": "Riverside Clinic"}
        )
        assert res.status_code == 200
        assert res.json()["name"] == "Riverside Clinic"

    def test_a_rejected_rename_leaves_the_name_untouched(self, client, make_project):
        make_project(name="Riverside Clinic")
        other = make_project(name="Bay St. Office")
        client.patch(
            f"/api/projects/{other['projectId']}", json={"new_name": "Riverside Clinic"}
        )
        names = {p["projectId"]: p["name"] for p in client.get("/api/projects/all_projects").json()}
        assert names[other["projectId"]] == "Bay St. Office"


class TestDeleteProject:
    """Deleting a project takes everything under it: its designs, their modules,
    and every blob those designs own."""

    def test_returns_204_with_no_body(self, client, project):
        res = client.delete(f"/api/projects/{project['projectId']}")
        assert res.status_code == 204
        assert res.content == b""

    def test_disappears_from_the_listing(self, client, project):
        client.delete(f"/api/projects/{project['projectId']}")
        assert client.get("/api/projects/all_projects").json() == []

    def test_an_empty_project_deletes_too(self, client, make_project):
        empty = make_project(name="Nothing Uploaded")
        assert client.delete(f"/api/projects/{empty['projectId']}").status_code == 204

    def test_takes_its_designs_with_it(self, client, project, upload_design):
        created = upload_design(project["projectId"])
        client.delete(f"/api/projects/{project['projectId']}")
        assert client.get(f"/api/designs/{created['designId']}").status_code == 404
        assert client.get(f"/api/projects/{project['projectId']}/designs").status_code == 404

    def test_takes_the_designs_modules_with_it(self, client, project, upload_design):
        created = upload_design(project["projectId"])
        # Attached directly rather than waiting for extraction to emit one: this
        # test is about the delete reaching the third level, and depending on the
        # processor's output would make it vacuous whenever that output is empty.
        _attach_module(created["designId"], "mod_cascade")
        client.delete(f"/api/projects/{project['projectId']}")
        res = client.patch("/api/modules/mod_cascade", json={"type": "X"})
        assert res.status_code == 404

    def test_takes_every_designs_blobs_with_it(self, client, project, upload_design):
        """Blobs are keyed per design, not per project — each design's prefix has
        to be wiped separately or its source IFC and module GLBs are orphaned in
        the bucket forever."""
        from app import blob

        store = blob.get_blob_store()
        designs = [
            upload_design(project["projectId"], name="One", filename="one.ifc"),
            upload_design(project["projectId"], name="Two", filename="two.ifc"),
        ]
        client.delete(f"/api/projects/{project['projectId']}")
        for d in designs:
            with pytest.raises(LookupError):
                store.source_ref(d["designId"])
            assert store.delete_prefix(blob.design_prefix(d["designId"])) == 0

    def test_leaves_another_projects_blobs_alone(self, client, make_project, upload_design):
        from app import blob

        store = blob.get_blob_store()
        keep = make_project(name="Keep")
        drop = make_project(name="Drop")
        kept = upload_design(keep["projectId"], name="Keep", filename="keep.ifc")
        upload_design(drop["projectId"], name="Drop", filename="drop.ifc")
        client.delete(f"/api/projects/{drop['projectId']}")
        assert store.source_ref(kept["designId"]).endswith("/keep.ifc")

    def test_blob_cleanup_failure_still_deletes_the_project(
        self, client, project, upload_design, monkeypatch
    ):
        """Storage is best-effort on the way out: the rows are already gone, so a
        failed wipe leaves orphans (recoverable) rather than a failed request."""
        from app import blob

        upload_design(project["projectId"])

        def _boom(_prefix):
            raise RuntimeError("gcs down")

        monkeypatch.setattr(blob.get_blob_store(), "delete_prefix", _boom)
        assert client.delete(f"/api/projects/{project['projectId']}").status_code == 204
        assert client.get("/api/projects/all_projects").json() == []

    def test_leaves_another_projects_designs_alone(self, client, make_project, upload_design):
        keep = make_project(name="Keep")
        drop = make_project(name="Drop")
        kept = upload_design(keep["projectId"])
        upload_design(drop["projectId"])
        client.delete(f"/api/projects/{drop['projectId']}")
        assert client.get(f"/api/designs/{kept['designId']}").status_code == 200

    def test_frees_the_name_for_reuse(self, client, make_project):
        project = make_project(name="Riverside Clinic")
        client.delete(f"/api/projects/{project['projectId']}")
        res = client.post(
            "/api/projects", json={"name": "Riverside Clinic", "location": "Elsewhere"}
        )
        assert res.status_code == 201

    def test_unknown_project_is_404(self, client):
        res = client.delete("/api/projects/prj_missing")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_deleting_twice_is_404(self, client, project):
        client.delete(f"/api/projects/{project['projectId']}")
        res = client.delete(f"/api/projects/{project['projectId']}")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_is_409_while_a_design_is_processing(
        self, client, project, upload_design, mark_processing
    ):
        """The worker settles the design and writes its GLBs after the request
        returns — deleting the project underneath it loses that write and strands
        whatever it was still producing."""
        created = upload_design(project["projectId"])
        mark_processing(created["designId"])
        res = client.delete(f"/api/projects/{project['projectId']}")
        assert res.status_code == 409
        assert res.json()["message"]

    def test_a_rejected_delete_leaves_everything_intact(
        self, client, project, upload_design, mark_processing
    ):
        from app import blob

        store = blob.get_blob_store()
        created = upload_design(project["projectId"])
        mark_processing(created["designId"])
        client.delete(f"/api/projects/{project['projectId']}")
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 1
        assert client.get(f"/api/designs/{created['designId']}").status_code == 200
        assert store.source_ref(created["designId"])

    def test_succeeds_once_processing_settles(self, client, project, upload_design):
        """The block is temporary — a project whose designs have all settled
        deletes normally."""
        upload_design(project["projectId"])  # settles COMPLETE under the TestClient
        assert client.delete(f"/api/projects/{project['projectId']}").status_code == 204

    def test_a_design_processing_elsewhere_does_not_block(
        self, client, make_project, upload_design, mark_processing
    ):
        keep = make_project(name="Busy")
        drop = make_project(name="Idle")
        busy = upload_design(keep["projectId"])
        mark_processing(busy["designId"])
        assert client.delete(f"/api/projects/{drop['projectId']}").status_code == 204
