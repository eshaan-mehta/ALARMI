"""End-to-end journeys — the sequences the product actually performs.

These drive the whole stack (ASGI app → routers → repositories → SQLite) exactly
as the web client does, in the order the UI does it. They exist to catch the
failures unit tests miss: state that doesn't line up between two endpoints,
counts that drift, deletes that leave debris.

Reference flows: `website/src/pages/ProjectsDashboard.tsx`, `ProjectDetail.tsx`
and the design doc §3.1.2 (upload → poll status → read metadata).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from conftest import STATUSES, UNIT_SCALES, ifc_bytes


def _upload(client, project_id, name, filename, size=None):
    return client.post(
        f"/api/projects/{project_id}/designs",
        data={"name": name},
        files={"file": (filename, ifc_bytes(size), "application/octet-stream")},
    )


class TestFullDesignLifecycle:
    def test_create_upload_track_read_edit_rename_delete(self, client):
        # 1. Dashboard starts empty.
        assert client.get("/api/projects/all_projects").json() == []

        # 2. The user creates a project.
        project = client.post(
            "/api/projects",
            json={"name": "Riverside Modular Clinic", "location": "Portland, OR"},
        ).json()
        project_id = project["projectId"]
        assert project["designCount"] == 0

        # 3. Opening the project shows no designs yet.
        assert client.get(f"/api/projects/{project_id}/designs").json() == []

        # 4. The user uploads an IFC file (FS1).
        res = _upload(client, project_id, "Ward A Headwall", "ward-a-headwall.ifc")
        assert res.status_code == 201
        design = res.json()
        design_id = design["designId"]

        # 5. The status badge polls until processing settles (FS2).
        status = client.get(f"/api/designs/{design_id}/status").json()["status"]
        assert status in STATUSES
        for _ in range(10):
            if status != "PROCESSING":
                break
            status = client.get(f"/api/designs/{design_id}/status").json()["status"]
        assert status == "COMPLETE"

        # 6. The design row shows up with a module count.
        listed = client.get(f"/api/projects/{project_id}/designs").json()
        assert len(listed) == 1
        assert listed[0]["designId"] == design_id
        assert listed[0]["moduleCount"] >= 1

        # 7. Expanding the row lazily fetches the extracted metadata (FS5).
        modules = client.get(f"/api/designs/{design_id}/modules").json()
        assert len(modules) == listed[0]["moduleCount"]
        assert all(m["unitScale"] in UNIT_SCALES for m in modules)

        # 8. The user corrects one module's metadata.
        module_id = modules[0]["moduleId"]
        edited = client.patch(
            f"/api/modules/{module_id}",
            json={
                "type": "Hospital Headwall",
                "dimensions": {"x": 3.6, "y": 1.4, "z": 0.2},
                "roomId": "IfcSpace_WardA_Bed01",
                "unitScale": "METRE",
            },
        )
        assert edited.status_code == 200

        # 9. The edit is visible on the next read, and nothing else moved.
        after = client.get(f"/api/designs/{design_id}/modules").json()
        assert next(m for m in after if m["moduleId"] == module_id)["type"] == "Hospital Headwall"
        assert len(after) == len(modules)
        assert client.get(f"/api/designs/{design_id}").json()["moduleCount"] == len(modules)

        # 10. The user renames the design (FS3).
        renamed = client.patch(f"/api/designs/{design_id}", json={"name": "Ward A — rev B"})
        assert renamed.status_code == 200
        assert renamed.json()["name"] == "Ward A — rev B"

        # 11. The project count reflects the single design.
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 1

        # 12. The user deletes the design (FS3) — it and its metadata are gone.
        assert client.delete(f"/api/designs/{design_id}").status_code == 204
        assert client.get(f"/api/designs/{design_id}").status_code == 404
        assert client.get(f"/api/designs/{design_id}/modules").status_code == 404
        assert client.patch(f"/api/modules/{module_id}", json={}).status_code == 404
        assert client.get(f"/api/projects/{project_id}/designs").json() == []
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 0


class TestMultiProjectIsolation:
    def test_two_projects_never_see_each_others_work(self, client):
        clinic = client.post(
            "/api/projects", json={"name": "Clinic", "location": "Portland, OR"}
        ).json()
        office = client.post(
            "/api/projects", json={"name": "Office", "location": "San Francisco, CA"}
        ).json()

        clinic_designs = [
            _upload(client, clinic["projectId"], f"Clinic {i}", f"clinic-{i}.ifc", 400 + i).json()
            for i in range(3)
        ]
        office_design = _upload(
            client, office["projectId"], "Office 1", "office-1.ifc", 500
        ).json()

        listed_clinic = client.get(f"/api/projects/{clinic['projectId']}/designs").json()
        listed_office = client.get(f"/api/projects/{office['projectId']}/designs").json()
        assert {d["designId"] for d in listed_clinic} == {d["designId"] for d in clinic_designs}
        assert {d["designId"] for d in listed_office} == {office_design["designId"]}

        counts = {p["projectId"]: p["designCount"] for p in client.get("/api/projects/all_projects").json()}
        assert counts[clinic["projectId"]] == 3
        assert counts[office["projectId"]] == 1

        # Deleting everything in one project leaves the other untouched.
        for design in clinic_designs:
            client.delete(f"/api/designs/{design['designId']}")
        assert client.get(f"/api/projects/{office['projectId']}/designs").json() == listed_office
        assert client.get(f"/api/designs/{office_design['designId']}").status_code == 200

        # Renaming one project doesn't disturb the other.
        client.patch(f"/api/projects/{clinic['projectId']}", json={"new_name": "Clinic v2"})
        names = {p["projectId"]: p["name"] for p in client.get("/api/projects/all_projects").json()}
        assert names[clinic["projectId"]] == "Clinic v2"
        assert names[office["projectId"]] == "Office"


class TestModuleIdentityAcrossDesigns:
    def test_module_ids_are_globally_unique(self, client):
        """Table 6 makes ModuleID a primary key, and the mobile app fetches
        modules by id alone (`/api/objects/get_url/{moduleId}`) — ids can't
        collide across designs or projects."""
        seen: set[str] = set()
        for p in range(2):
            project = client.post(
                "/api/projects", json={"name": f"P{p}", "location": "X"}
            ).json()
            for d in range(3):
                design = _upload(
                    client, project["projectId"], f"D{d}", f"d{d}.ifc", 300 + d
                ).json()
                ids = [
                    m["moduleId"]
                    for m in client.get(f"/api/designs/{design['designId']}/modules").json()
                ]
                assert seen.isdisjoint(ids)
                seen.update(ids)
        assert len(seen) >= 6


class TestPersistence:
    def test_data_survives_a_restart(self, client):
        """NFS3 aside, this is the point of a database: state outlives the
        process. Phase 1 must not behave like the in-memory mock it replaced."""
        project = client.post(
            "/api/projects", json={"name": "Persisted", "location": "Waterloo, ON"}
        ).json()
        design = _upload(client, project["projectId"], "Persisted design", "p.ifc").json()
        modules = client.get(f"/api/designs/{design['designId']}/modules").json()
        client.patch(f"/api/modules/{modules[0]['moduleId']}", json={"type": "Wall Panel"})

        with TestClient(app) as restarted:  # new lifespan, same database file
            assert [p["projectId"] for p in restarted.get("/api/projects/all_projects").json()] == [
                project["projectId"]
            ]
            reread = restarted.get(f"/api/designs/{design['designId']}").json()
            assert reread == design
            after = restarted.get(f"/api/designs/{design['designId']}/modules").json()
            assert next(m for m in after if m["moduleId"] == modules[0]["moduleId"])["type"] == "Wall Panel"


class TestRepeatedOperations:
    def test_upload_and_delete_cycles_do_not_drift(self, client):
        """Counts must be derived, not accumulated."""
        project = client.post("/api/projects", json={"name": "Churn", "location": "X"}).json()
        for i in range(5):
            design = _upload(client, project["projectId"], f"D{i}", f"d{i}.ifc", 300 + i).json()
            assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 1
            client.delete(f"/api/designs/{design['designId']}")
            assert client.get("/api/projects/all_projects").json()[0]["designCount"] == 0
        assert client.get(f"/api/projects/{project['projectId']}/designs").json() == []

    def test_repeated_renames_settle_on_the_last_value(self, client):
        project = client.post("/api/projects", json={"name": "A", "location": "X"}).json()
        for name in ("B", "C", "D"):
            client.patch(f"/api/projects/{project['projectId']}", json={"new_name": name})
        assert client.get("/api/projects/all_projects").json()[0]["name"] == "D"

    @pytest.mark.parametrize("count", [10])
    def test_a_project_holds_many_designs(self, client, count):
        project = client.post("/api/projects", json={"name": "Big", "location": "X"}).json()
        for i in range(count):
            assert _upload(client, project["projectId"], f"D{i}", f"d{i}.ifc", 300 + i).status_code == 201
        listed = client.get(f"/api/projects/{project['projectId']}/designs").json()
        assert len(listed) == count
        assert len({d["designId"] for d in listed}) == count
        assert client.get("/api/projects/all_projects").json()[0]["designCount"] == count
