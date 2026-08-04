"""Cross-cutting API contract: error shape, CORS, health, routing.

Every client in the system reads failures the same way — the web app does
`err.response?.data?.message` in all five of its modals — so *every* error the
API can emit has to carry a `message` string. The design doc (§3.2.2) also fixes
the coarse contract: 2xx success, 4xx client error, 5xx server error.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.projects import repository as projects_repo


class TestHealth:
    def test_reports_ok(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_needs_no_database_rows(self, client):
        """Used as a liveness probe by the host — must answer on an empty DB."""
        assert client.get("/api/health").status_code == 200


class TestErrorShape:
    """`{ "message": ... }`, for anything a client can trip."""

    def _bodies(self, client, project):
        return [
            client.post("/api/projects", json={"name": "", "location": ""}),  # 400
            client.get("/api/designs/dsn_missing"),  # 404
            client.patch("/api/projects/prj_missing", json={"new_name": "x"}),  # 404
            client.patch("/api/modules/mod_missing", json={"type": "x"}),  # 404
            client.delete("/api/designs/dsn_missing"),  # 404
        ]

    def test_handled_errors_carry_a_message(self, client, project):
        for res in self._bodies(client, project):
            assert 400 <= res.status_code < 500
            assert isinstance(res.json().get("message"), str)
            assert res.json()["message"]

    @pytest.mark.parametrize(
        "body",
        [
            {"name": 123, "location": "Portland"},
            {"name": ["Clinic"], "location": "Portland"},
            {"name": "Clinic", "location": {"city": "Portland"}},
        ],
    )
    def test_schema_violations_also_carry_a_message(self, client, body):
        """A malformed body falls through to FastAPI's own `{"detail": [...]}`,
        which every client modal renders as a blank error. The status code is
        the framework's business (400 or 422); the body shape is ours."""
        res = client.post("/api/projects", json=body)
        assert 400 <= res.status_code < 500
        assert isinstance(res.json().get("message"), str)

    def test_malformed_json_carries_a_message(self, client):
        res = client.post(
            "/api/projects",
            content=b"{not json",
            headers={"content-type": "application/json"},
        )
        assert 400 <= res.status_code < 500
        assert isinstance(res.json().get("message"), str)

    def test_an_unknown_api_route_carries_a_message(self, client):
        res = client.get("/api/nope")
        assert res.status_code == 404
        assert isinstance(res.json().get("message"), str)

    def test_a_wrong_method_carries_a_message(self, client, project):
        # PUT, not DELETE: the path now serves PATCH (rename) and DELETE, so PUT
        # is the verb left over to prove an unsupported method answers in JSON.
        res = client.put(f"/api/projects/{project['projectId']}", json={})
        assert res.status_code in (404, 405)
        assert isinstance(res.json().get("message"), str)

    def test_an_unexpected_failure_is_a_5xx_with_a_message(self, monkeypatch):
        """An internal fault must not leak a stack trace or an HTML page — the
        client still needs a message to show."""

        def boom(db):
            raise RuntimeError("database on fire")

        monkeypatch.setattr(projects_repo, "list_projects", boom)
        with TestClient(app, raise_server_exceptions=False) as unguarded:
            res = unguarded.get("/api/projects/all_projects")
        assert res.status_code == 500
        assert res.headers["content-type"].startswith("application/json")
        assert isinstance(res.json().get("message"), str)
        assert "database on fire" not in res.text  # no internals leaked


class TestCors:
    """NFS2: the dashboard runs in a plain browser, so the Vite dev origin has
    to survive preflight for every method the client uses."""

    ORIGIN = "http://localhost:5173"

    @pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
    def test_preflight_is_allowed_for_every_method_used(self, client, method):
        res = client.options(
            "/api/projects",
            headers={
                "Origin": self.ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert res.status_code in (200, 204)
        assert res.headers.get("access-control-allow-origin") == self.ORIGIN

    def test_simple_requests_get_the_origin_header(self, client):
        res = client.get("/api/projects/all_projects", headers={"Origin": self.ORIGIN})
        assert res.headers.get("access-control-allow-origin") == self.ORIGIN

    def test_error_responses_are_also_cors_enabled(self, client):
        """Without the header the browser hides the body, so the modal can't
        show why the request failed."""
        res = client.get("/api/designs/dsn_missing", headers={"Origin": self.ORIGIN})
        assert res.status_code == 404
        assert res.headers.get("access-control-allow-origin") == self.ORIGIN

    def test_an_unlisted_origin_is_not_granted_access(self, client):
        res = client.get(
            "/api/projects/all_projects", headers={"Origin": "http://evil.example"}
        )
        assert res.headers.get("access-control-allow-origin") != "http://evil.example"


class TestRouting:
    def test_every_documented_route_is_mounted_under_api(self, client):
        paths = set(client.get("/openapi.json").json()["paths"])
        assert {
            "/api/health",
            "/api/projects/all_projects",
            "/api/projects",
            "/api/projects/{project_id}",
            "/api/projects/{project_id}/designs",
            "/api/designs/{design_id}",
            "/api/designs/{design_id}/status",
            "/api/designs/{design_id}/modules",
            "/api/modules/{module_id}",
            "/api/objects/get_url/{module_id}",
        } <= paths

    def test_interactive_docs_are_served(self, client):
        assert client.get("/docs").status_code == 200
