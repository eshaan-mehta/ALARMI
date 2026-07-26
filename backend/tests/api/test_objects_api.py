"""Endpoint tests for the AR object URL (design doc Table 4).

`GET /api/objects/get_url/{moduleId}` — the mobile app opens a module in AR by
following a presigned URL to its GLB in blob storage. This is the one endpoint
mobile needs that the web app doesn't: the web renders metadata in a modal, the
mobile app renders the actual 3D object.
"""


def _a_module_id(client, design) -> str:
    return client.get(f"/api/designs/{design['designId']}/modules").json()[0]["moduleId"]


class TestObjectUrl:
    def test_returns_a_url_for_a_real_module(self, client, design):
        res = client.get(f"/api/objects/get_url/{_a_module_id(client, design)}")
        assert res.status_code == 200
        assert res.json()["url"].startswith("http")

    def test_url_is_scoped_to_the_module(self, client, design):
        module_id = _a_module_id(client, design)
        url = client.get(f"/api/objects/get_url/{module_id}").json()["url"]
        assert module_id in url

    def test_unknown_module_is_404_with_a_message(self, client):
        res = client.get("/api/objects/get_url/mod_missing")
        assert res.status_code == 404
        assert res.json()["message"]

    def test_distinct_modules_get_distinct_urls(self, client, design):
        modules = client.get(f"/api/designs/{design['designId']}/modules").json()
        if len(modules) < 2:
            return  # the stub yields 1..3; only assert when there are two
        a = client.get(f"/api/objects/get_url/{modules[0]['moduleId']}").json()["url"]
        b = client.get(f"/api/objects/get_url/{modules[1]['moduleId']}").json()["url"]
        assert a != b
