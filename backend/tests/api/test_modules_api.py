"""Endpoint tests for editing module metadata.

`PATCH /api/modules/{moduleId}` is a deliberate extension of the design doc
(Table 6 stores the metadata per module; the doc's file-level operations stop at
view/rename/delete). The editor lives in `website/src/components/EditModuleModal.tsx`,
which sends only the fields it has values for and re-scales dimensions when the
unit changes — so the unit the client sends must be one it can convert.
"""

import pytest

from conftest import MODULE_FIELDS, UNIT_SCALES


@pytest.fixture
def module(client, design) -> dict:
    return client.get(f"/api/designs/{design['designId']}/modules").json()[0]


class TestUpdateModule:
    def test_returns_the_updated_module(self, client, module):
        res = client.patch(
            f"/api/modules/{module['moduleId']}", json={"type": "Hospital Headwall"}
        )
        assert res.status_code == 200
        assert set(res.json()) == MODULE_FIELDS
        assert res.json()["type"] == "Hospital Headwall"

    def test_persists_to_the_modules_endpoint(self, client, design, module):
        client.patch(f"/api/modules/{module['moduleId']}", json={"type": "Wall Panel"})
        modules = client.get(f"/api/designs/{design['designId']}/modules").json()
        edited = next(m for m in modules if m["moduleId"] == module["moduleId"])
        assert edited["type"] == "Wall Panel"

    def test_updates_dimensions(self, client, module):
        res = client.patch(
            f"/api/modules/{module['moduleId']}",
            json={"dimensions": {"x": 3.6, "y": 1.4, "z": 0.2}},
        )
        assert res.json()["dimensions"] == {"x": 3.6, "y": 1.4, "z": 0.2}

    def test_updates_room_id_and_unit_scale(self, client, module):
        res = client.patch(
            f"/api/modules/{module['moduleId']}",
            json={"roomId": "IfcSpace_WardA_Bed01", "unitScale": "CENTIMETRE"},
        )
        assert res.json()["roomId"] == "IfcSpace_WardA_Bed01"
        assert res.json()["unitScale"] == "CENTIMETRE"

    def test_is_a_partial_update(self, client, module):
        """Fields the modal didn't send must survive untouched."""
        res = client.patch(f"/api/modules/{module['moduleId']}", json={"type": "Wall Panel"})
        body = res.json()
        assert body["dimensions"] == module["dimensions"]
        assert body["roomId"] == module["roomId"]
        assert body["unitScale"] == module["unitScale"]

    def test_the_full_editor_payload_round_trips(self, client, module):
        """Exactly what `EditModuleModal` submits."""
        patch = {
            "type": "Bathroom Service Wall",
            "dimensions": {"x": 2.4, "y": 2.7, "z": 0.15},
            "roomId": "IfcSpace_WardA_WC",
            "unitScale": "METRE",
        }
        res = client.patch(f"/api/modules/{module['moduleId']}", json=patch)
        assert res.status_code == 200
        assert {k: res.json()[k] for k in patch} == patch

    def test_an_empty_patch_is_a_no_op(self, client, module):
        res = client.patch(f"/api/modules/{module['moduleId']}", json={})
        assert res.status_code == 200
        assert res.json() == module

    def test_unknown_module_is_404(self, client):
        res = client.patch("/api/modules/mod_missing", json={"type": "Wall Panel"})
        assert res.status_code == 404
        assert res.json()["message"]

    def test_does_not_change_the_designs_module_count(self, client, design, module):
        client.patch(f"/api/modules/{module['moduleId']}", json={"type": "Wall Panel"})
        current = client.get(f"/api/designs/{design['designId']}").json()
        assert current["moduleCount"] == design["moduleCount"]

    def test_does_not_touch_sibling_modules(self, client, design, module):
        before = client.get(f"/api/designs/{design['designId']}/modules").json()
        client.patch(f"/api/modules/{module['moduleId']}", json={"type": "Wall Panel"})
        after = client.get(f"/api/designs/{design['designId']}/modules").json()
        for old, new in zip(before, after):
            if old["moduleId"] != module["moduleId"]:
                assert old == new

    def test_the_module_id_is_not_writable(self, client, module):
        res = client.patch(
            f"/api/modules/{module['moduleId']}",
            json={"moduleId": "mod_hijacked", "type": "Wall Panel"},
        )
        assert res.status_code in (200, 400)
        assert client.patch("/api/modules/mod_hijacked", json={}).status_code == 404


class TestUpdateModuleValidation:
    @pytest.mark.parametrize(
        "dimensions",
        [
            {"x": 0, "y": 1, "z": 1},
            {"x": -1, "y": 1, "z": 1},
            {"x": 1, "y": 0, "z": 1},
            {"x": 1, "y": 1, "z": -0.5},
        ],
    )
    def test_rejects_non_positive_dimensions(self, client, module, dimensions):
        """A module is a physical object: the robot marks its footprint and the
        app renders it at 1:1. A zero or negative extent is not a real module."""
        res = client.patch(f"/api/modules/{module['moduleId']}", json={"dimensions": dimensions})
        assert res.status_code == 400
        assert res.json()["message"]

    @pytest.mark.parametrize(
        "dimensions",
        [{"x": 1, "y": 1}, {"x": 1, "y": 1, "z": "wide"}, {"x": 1, "y": 1, "z": None}, []],
    )
    def test_rejects_malformed_dimensions(self, client, module, dimensions):
        res = client.patch(f"/api/modules/{module['moduleId']}", json={"dimensions": dimensions})
        assert 400 <= res.status_code < 500
        assert res.json()["message"]  # schema rejections need a message too

    @pytest.mark.parametrize("unit", ["PARSEC", "metre", "m", ""])
    def test_rejects_a_unit_the_client_cannot_convert(self, client, module, unit):
        """`website/src/lib/units.ts` converts and labels five unit scales; an
        unknown one silently breaks the dimension display and conversion."""
        res = client.patch(f"/api/modules/{module['moduleId']}", json={"unitScale": unit})
        assert res.status_code == 400
        assert res.json()["message"]

    @pytest.mark.parametrize("unit", sorted(UNIT_SCALES))
    def test_accepts_every_supported_unit(self, client, module, unit):
        res = client.patch(f"/api/modules/{module['moduleId']}", json={"unitScale": unit})
        assert res.status_code == 200
        assert res.json()["unitScale"] == unit

    @pytest.mark.policy
    def test_a_rejected_edit_changes_nothing(self, client, module):
        client.patch(
            f"/api/modules/{module['moduleId']}",
            json={"type": "Wall Panel", "dimensions": {"x": -1, "y": 1, "z": 1}},
        )
        after = client.patch(f"/api/modules/{module['moduleId']}", json={}).json()
        assert after == module

    @pytest.mark.policy
    def test_blank_text_clears_the_field_rather_than_storing_whitespace(self, client, module):
        """The editor sends `undefined` for an empty box, but a whitespace-only
        value must not be stored as if it were metadata."""
        res = client.patch(
            f"/api/modules/{module['moduleId']}", json={"type": "   ", "roomId": "  "}
        )
        assert res.status_code == 200
        assert res.json()["type"] is None
        assert res.json()["roomId"] is None
