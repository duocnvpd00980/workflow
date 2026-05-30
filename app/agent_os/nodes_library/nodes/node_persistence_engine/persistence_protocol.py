from pydantic import BaseModel


class PersistencePayload(BaseModel):
    persisted: bool

    storage_backend: str
