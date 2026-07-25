"""End-to-end against a real uvicorn process over real HTTP.

`TestClient` speaks ASGI in-process, which skips the parts a browser actually
depends on: the HTTP/1.1 server, real multipart streaming over a socket, and the
CORS headers as they land on the wire. This module runs the server the same way
`uv run dev` does and talks to it with an HTTP client.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

from conftest import ifc_bytes

ORIGIN = "http://localhost:5173"

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_url(tmp_path_factory):
    """A real uvicorn process, started the way `uv run dev` starts it.

    It runs out-of-process against its own database file, so nothing it does can
    touch the in-process engine the rest of the suite shares.
    """
    port = _free_port()
    db_path = tmp_path_factory.mktemp("live") / "live.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}", "APP_ENV": "test"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=BACKEND_DIR,
        env=env,
    )

    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"uvicorn exited early with code {proc.returncode}")
        try:
            if httpx.get(f"{base}/api/health", timeout=1).status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("uvicorn did not come up in time")

    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.live
class TestOverRealHttp:
    def test_health_check(self, live_url):
        assert httpx.get(f"{live_url}/api/health", timeout=5).json() == {"status": "ok"}

    def test_browser_workflow(self, live_url):
        """The dashboard's real sequence, with the browser's Origin header on
        every request."""
        headers = {"Origin": ORIGIN}

        preflight = httpx.options(
            f"{live_url}/api/projects",
            headers={
                **headers,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=5,
        )
        assert preflight.status_code in (200, 204)
        assert preflight.headers.get("access-control-allow-origin") == ORIGIN

        created = httpx.post(
            f"{live_url}/api/projects",
            json={"name": "Live Clinic", "location": "Portland, OR"},
            headers=headers,
            timeout=5,
        )
        assert created.status_code == 201
        assert created.headers.get("access-control-allow-origin") == ORIGIN
        project_id = created.json()["projectId"]

        uploaded = httpx.post(
            f"{live_url}/api/projects/{project_id}/designs",
            data={"name": "Ward A"},
            files={"file": ("ward-a.ifc", ifc_bytes(4096), "application/octet-stream")},
            headers=headers,
            timeout=30,
        )
        assert uploaded.status_code == 201
        design = uploaded.json()
        assert design["fileSize"] == 4096

        status = httpx.get(f"{live_url}/api/designs/{design['designId']}/status", timeout=5)
        assert status.status_code == 200

        modules = httpx.get(f"{live_url}/api/designs/{design['designId']}/modules", timeout=5)
        assert modules.status_code == 200
        assert len(modules.json()) == design["moduleCount"]

        deleted = httpx.delete(f"{live_url}/api/designs/{design['designId']}", timeout=5)
        assert deleted.status_code == 204

    def test_errors_reach_the_browser_with_a_message(self, live_url):
        res = httpx.get(f"{live_url}/api/designs/dsn_missing", headers={"Origin": ORIGIN}, timeout=5)
        assert res.status_code == 404
        assert res.json()["message"]
        assert res.headers.get("access-control-allow-origin") == ORIGIN

    def test_concurrent_requests_are_served(self, live_url):
        """FastAPI runs sync handlers in a threadpool sharing one SQLite file;
        parallel dashboard polling must not deadlock or error."""
        project = httpx.post(
            f"{live_url}/api/projects",
            json={"name": "Concurrent", "location": "X"},
            timeout=5,
        ).json()
        for i in range(3):
            httpx.post(
                f"{live_url}/api/projects/{project['projectId']}/designs",
                data={"name": f"D{i}"},
                files={"file": (f"d{i}.ifc", ifc_bytes(1000 + i), "application/octet-stream")},
                timeout=30,
            )

        results: list[int] = []
        errors: list[Exception] = []

        def poll():
            try:
                for _ in range(5):
                    results.append(
                        httpx.get(f"{live_url}/api/projects/{project['projectId']}/designs", timeout=10).status_code
                    )
            except Exception as exc:  # noqa: BLE001 — recorded and re-raised below
                errors.append(exc)

        threads = [threading.Thread(target=poll) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, errors
        assert results and set(results) == {200}

    def test_concurrent_uploads_all_persist(self, live_url):
        """Two users uploading at once must both get their design — no lost
        writes and no 500s from the shared connection."""
        project = httpx.post(
            f"{live_url}/api/projects", json={"name": "Race", "location": "X"}, timeout=5
        ).json()
        statuses: list[int] = []

        def upload(i: int):
            res = httpx.post(
                f"{live_url}/api/projects/{project['projectId']}/designs",
                data={"name": f"D{i}"},
                files={"file": (f"d{i}.ifc", ifc_bytes(2000 + i), "application/octet-stream")},
                timeout=30,
            )
            statuses.append(res.status_code)

        threads = [threading.Thread(target=upload, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert set(statuses) == {201}
        listed = httpx.get(f"{live_url}/api/projects/{project['projectId']}/designs", timeout=10).json()
        assert len(listed) == 6

    def test_duplicate_project_names_race_to_a_single_winner(self, live_url):
        """Uniqueness has to hold under concurrency, and the losers must get a
        409 rather than a 500."""
        statuses: list[int] = []

        def create():
            statuses.append(
                httpx.post(
                    f"{live_url}/api/projects",
                    json={"name": "Contended", "location": "X"},
                    timeout=10,
                ).status_code
            )

        threads = [threading.Thread(target=create) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert statuses.count(201) == 1
        assert set(statuses) <= {201, 409}
        names = [p["name"] for p in httpx.get(f"{live_url}/api/projects/all_projects", timeout=10).json()]
        assert names.count("Contended") == 1
