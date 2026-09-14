from pydantic import BaseModel, Field, field_validator

class PolishInput(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请提供需要润色的主线节点")
        return value


class PolishResult(PolishInput):
    prompts: list[str] = Field(max_length=3)