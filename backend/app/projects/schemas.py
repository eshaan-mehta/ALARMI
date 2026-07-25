from pydantic import BaseModel


class ProjectOut(BaseModel):
    projectId: str
    name: str
    location: str
    designCount: int
    createdTime: str


class ProjectCreate(BaseModel):
    name: str | None = None
    location: str | None = None


class ProjectRename(BaseModel):
    new_name: str | None = None
