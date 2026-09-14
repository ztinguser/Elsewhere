from pydantic import BaseModel, field_validator


class MemoryInput(BaseModel):
    time_text: str
    content: str

    @field_validator("time_text", "content")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("时间和事件内容不能为空")
        return value