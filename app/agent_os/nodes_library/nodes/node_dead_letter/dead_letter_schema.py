from pydantic import BaseModel


class DeadLetterPayload(BaseModel):
    failed_node: str

    error_code: str

    error_message: str
