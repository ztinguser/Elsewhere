from pydantic import BaseModel, Field, model_validator


class DecisionInput(BaseModel):
    option_index: int | None = Field(default=None, ge=0, strict=True)
    custom_decision: str = ""

    @model_validator(mode="after")
    def require_one_decision(self):
        self.custom_decision = self.custom_decision.strip()
        if (self.option_index is not None) == bool(self.custom_decision):
            raise ValueError("请选择一个选项或填写自己的决定，二者只能选择一个")
        return self


def resolve_decision(options: list[str], data: DecisionInput) -> str:
    if data.option_index is None:
        return data.custom_decision

    if data.option_index >= len(options):
        raise ValueError("所选选项不存在")

    return options[data.option_index]