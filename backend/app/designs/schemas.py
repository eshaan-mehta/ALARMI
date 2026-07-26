from pydantic import BaseModel


class DesignOut(BaseModel):
    designId: str
    projectId: str
    name: str
    fileName: str
    fileSize: int
    status: str
    uploadTime: str
    moduleCount: int


class DesignRename(BaseModel):
    name: str | None = None


class StatusOut(BaseModel):
    status: str
