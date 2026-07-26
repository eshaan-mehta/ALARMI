from pydantic import BaseModel


class ObjectUrlOut(BaseModel):
    # A presigned URL to the module's GLB in blob storage. The AR viewer follows
    # it directly, so the client never sees a storage key or credential.
    url: str
