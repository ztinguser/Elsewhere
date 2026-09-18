from pydantic import BaseModel, Field


class ArchiveConfirm(BaseModel):
    expected_revision: int = Field(ge=1)