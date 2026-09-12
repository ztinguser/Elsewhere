from pydantic import BaseModel, Field


class EventData(BaseModel):
    summary: str
    mechanism: str
    time_text: str | None = None
    preconditions: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    state_before: dict = Field(default_factory=dict)
    state_after: dict = Field(default_factory=dict)
    uncertainty: str = ""