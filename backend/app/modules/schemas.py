from pydantic import BaseModel


class Dimensions(BaseModel):
    x: float
    y: float
    z: float


class ModuleOut(BaseModel):
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
