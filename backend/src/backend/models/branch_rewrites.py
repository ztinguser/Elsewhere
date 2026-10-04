from pydantic import BaseModel, Field

from backend.models.decisions import DecisionInput


class BranchRewriteInput(BaseModel):
    request_id: str = Field(min_length=1)
    decision: DecisionInput
