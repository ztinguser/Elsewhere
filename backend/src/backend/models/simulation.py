from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from backend.models.events import EventData


class ChoiceData(BaseModel):
    situation: str
    options: list[str] = Field(min_length=2, max_length=3)


class StageData(BaseModel):
    # 本阶段发生的事件，至少一条
    events: list[EventData] = Field(min_length=1)
    # 本阶段停在什么时间
    end_time_text: str
    # 为什么停止推进
    end_reason: Literal["choice", "target"]
    # 停下时的处境和建议选项
    choice: ChoiceData | None

    @model_validator(mode="after")
    def check_ending(self):
        if (self.end_reason == "choice") != (self.choice is not None):
            raise ValueError("阶段停止原因与选择节点不一致")
        return self


class StageReview(BaseModel):
    model_config = {"extra": "forbid"}

    issues: list[str]

    @field_validator("issues")
    @classmethod
    def require_clear_issues(cls, issues: list[str]) -> list[str]:
        issues = [issue.strip() for issue in issues]
        if any(not issue for issue in issues):
            raise ValueError("校验问题不能为空白")
        return issues

    @property
    def approved(self) -> bool:
        return not self.issues