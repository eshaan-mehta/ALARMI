from pydantic import BaseModel

# The unit vocabulary the frontend can convert/label (website src/lib/units.ts).
# A value outside this set would make the client's display silently wrong.
UNIT_SCALES = {"METRE", "MILLIMETRE", "CENTIMETRE", "FOOT", "INCH"}


class Dimensions(BaseModel):
    # Types are enforced here (missing/non-numeric → 422); the positive-value
    # rule is a semantic check in the router so it returns a 400 with a message.
    x: float
    y: float
    z: float


class ModuleOut(BaseModel):
    # Lenient on read — serialises whatever is stored.
    moduleId: str
    type: str | None = None
    dimensions: Dimensions | None = None
    roomId: str | None = None
    unitScale: str | None = None


class ModulePatch(BaseModel):
    type: str | None = None
    dimensions: Dimensions | None = None
    roomId: str | None = None
    unitScale: str | None = None
