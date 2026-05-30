from pydantic import BaseModel
from typing import Any


class EventPayload(BaseModel):
    event_name: str

    event_data: Any
