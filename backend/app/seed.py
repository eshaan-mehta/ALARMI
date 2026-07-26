"""Optional demo data.

Run once to populate an empty DB so the dashboard isn't blank:

    uv run python -m app.seed

Not run on startup. Skips if any project already exists. These are hand-authored
sample rows (ported from the old MSW mock) — real data arrives via the API.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .db import SessionLocal, init_db
from .designs.models import Design
from .modules.models import Module
from .projects.models import Project


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.scalar(select(Project)) is not None:
            print("DB already has data — skipping seed.")
            return

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        clinic = Project(
            project_id="prj_seed_clinic",
            name="Riverside Modular Clinic",
            location="Portland, OR",
            created_time=_iso(day_ago),
        )
        office = Project(
            project_id="prj_seed_office",
            name="Bay St. Office Retrofit",
            location="San Francisco, CA",
            created_time=_iso(hour_ago),
        )
        db.add_all([clinic, office])

        designs = [
            Design(
                design_id="dsn_seed1",
                project_id=clinic.project_id,
                name="Ward A Headwall",
                file_name="ward-a-headwall.ifc",
                file_size=42_500_000,
                status="COMPLETE",
                upload_time=_iso(day_ago),
            ),
            Design(
                design_id="dsn_seed2",
                project_id=clinic.project_id,
                name="Corridor Utility Panel",
                file_name="corridor-utility.ifc",
                file_size=18_900_000,
                status="COMPLETE",
                upload_time=_iso(hour_ago),
            ),
            Design(
                design_id="dsn_seed3",
                project_id=clinic.project_id,
                name="Nurse Station Wall",
                file_name="nurse-station.ifc",
                file_size=27_300_000,
                status="COMPLETE",
                upload_time=_iso(day_ago - timedelta(seconds=10)),
            ),
            Design(
                design_id="dsn_seed4",
                project_id=office.project_id,
                name="Level 3 Partition Set",
                file_name="level-3-partitions.ifc",
                file_size=33_100_000,
                status="COMPLETE",
                upload_time=_iso(hour_ago),
            ),
            Design(
                design_id="dsn_seed5",
                project_id=office.project_id,
                name="Server Room Service Wall",
                file_name="server-room-service-wall.ifc",
                file_size=21_700_000,
                status="COMPLETE",
                upload_time=_iso(day_ago),
            ),
        ]
        db.add_all(designs)

        modules = [
            # Ward A Headwall
            Module(module_id="mod_seed_wardA_1", design_id="dsn_seed1", type="Hospital Headwall",
                   dimensions={"x": 3.6, "y": 1.4, "z": 0.2}, room_id="IfcSpace_WardA_Bed01", unit_scale="METRE"),
            Module(module_id="mod_seed_wardA_2", design_id="dsn_seed1", type="Hospital Headwall",
                   dimensions={"x": 3.6, "y": 1.4, "z": 0.2}, room_id="IfcSpace_WardA_Bed02", unit_scale="METRE"),
            Module(module_id="mod_seed_wardA_3", design_id="dsn_seed1", type="Bathroom Service Wall",
                   dimensions={"x": 2.4, "y": 2.7, "z": 0.15}, room_id="IfcSpace_WardA_WC", unit_scale="METRE"),
            # Corridor Utility Panel
            Module(module_id="mod_seed_corridor_1", design_id="dsn_seed2", type="Utility Panel",
                   dimensions={"x": 1.2, "y": 2.7, "z": 0.25}, room_id="IfcSpace_Corridor_L1", unit_scale="METRE"),
            Module(module_id="mod_seed_corridor_2", design_id="dsn_seed2", type="Utility Panel",
                   dimensions={"x": 1.2, "y": 2.7, "z": 0.25}, room_id="IfcSpace_Corridor_L1", unit_scale="METRE"),
            # Nurse Station Wall
            Module(module_id="mod_seed_nurse_1", design_id="dsn_seed3", type="Utility Panel",
                   dimensions={"x": 2.8, "y": 2.7, "z": 0.2}, room_id="IfcSpace_NurseStn_L1", unit_scale="METRE"),
            Module(module_id="mod_seed_nurse_2", design_id="dsn_seed3", type="Wall Panel",
                   dimensions={"x": 1.6, "y": 2.7, "z": 0.1}, room_id="IfcSpace_NurseStn_L1", unit_scale="METRE"),
            # Level 3 Partition Set
            Module(module_id="mod_seed_l3_1", design_id="dsn_seed4", type="Wall Panel",
                   dimensions={"x": 2.4, "y": 3.0, "z": 0.1}, room_id="IfcSpace_L3_OpenPlan", unit_scale="METRE"),
            Module(module_id="mod_seed_l3_2", design_id="dsn_seed4", type="Wall Panel",
                   dimensions={"x": 2.4, "y": 3.0, "z": 0.1}, room_id="IfcSpace_L3_OpenPlan", unit_scale="METRE"),
            Module(module_id="mod_seed_l3_3", design_id="dsn_seed4", type="Wall Panel",
                   dimensions={"x": 1.8, "y": 3.0, "z": 0.1}, room_id="IfcSpace_L3_MeetingRm", unit_scale="METRE"),
            # Server Room Service Wall
            Module(module_id="mod_seed_srv_1", design_id="dsn_seed5", type="Utility Panel",
                   dimensions={"x": 2.0, "y": 2.7, "z": 0.3}, room_id="IfcSpace_L3_ServerRm", unit_scale="METRE"),
            Module(module_id="mod_seed_srv_2", design_id="dsn_seed5", type="Bathroom Service Wall",
                   dimensions={"x": 1.6, "y": 2.7, "z": 0.15}, room_id="IfcSpace_L3_WC", unit_scale="METRE"),
        ]
        db.add_all(modules)

        db.commit()
        print("Seeded 2 projects, 5 designs, 12 modules.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
