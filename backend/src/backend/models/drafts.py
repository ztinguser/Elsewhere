from pydantic import BaseModel, Field


class DraftInput(BaseModel):
    time_text: str
    content: str
    expected_revision: int = Field(ge=0)