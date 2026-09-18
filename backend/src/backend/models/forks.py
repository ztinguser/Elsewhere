from pydantic import BaseModel, Field, field_validator


class ForkInput(BaseModel):
    request_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    alternative: str
    expected_revision: int = Field(ge=1)

    @field_validator("alternative")
    @classmethod
    def require_alternative(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("替代决定不能为空")
        return value