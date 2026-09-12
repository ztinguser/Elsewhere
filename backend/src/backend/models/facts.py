from pydantic import BaseModel


class FactData(BaseModel):
    content: str
    kind: str
    time_text: str | None = None
    occurred_from: str | None = None
    occurred_to: str | None = None
    uncertainty: str | None = None