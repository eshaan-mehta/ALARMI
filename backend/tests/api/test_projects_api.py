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

from app.projects import repository as projects_repo
from conftest import PROJECT_FIELDS


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
