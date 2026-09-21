from pydantic import BaseModel, Field


class PlanFact(BaseModel):
    fact_id: str
    detail: str


class ForkQuestion(BaseModel):
    question: str
    reason: str
    assumption: str


class ForkPlan(BaseModel):
    # 明确替换的决定，以及有没有额外假设成功结果
    change: str
    # 分叉时可以保留的真实条件
    preserved: list[PlanFact]
    # 受到替代决定影响、需要重新判断的后续经历
    affected: list[PlanFact]
    # 回忆中已有依据的外部背景条件
    external_conditions: list[PlanFact]
    # 哪些信息不能当作分叉时已知条件
    information_limits: list[PlanFact]
    # 需要在最终方案中明确确认的额外假设
    assumptions: list[str]
    # 一次展示的零到三个补问
    questions: list[ForkQuestion] = Field(max_length=3)
    # 无法靠合理假设解决、需要先修正的问题
    blockers: list[str]


class ForkPlanConfirm(BaseModel):
    expected_revision: int = Field(ge=1)