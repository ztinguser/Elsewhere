import json

from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.fork_plan import ForkPlan
from backend.prompts.fork_plan import SYSTEM_PROMPT
from backend.prompts.fork_plan_final import SYSTEM_PROMPT as FINAL_PROMPT


async def generate_fork_plan(
    client: ModelClient,
    branch: dict,
    snapshot: dict,
    *,
    initial_plan: dict | None = None,
    answers: list[dict] | None = None,
) -> dict:
    if (initial_plan is None) != (answers is None):
        raise ValueError("原始方案和问卷答案必须一起提供")

    facts = [
        {
            "id": fact["id"],
            "time_text": fact.get("time_text"),
            "content": fact["content"],
        }
        for fact in snapshot["facts"]
    ]
    context = {
        "fork_fact_id": branch["fork_fact_id"],
        "alternative": branch["alternative"],
        "target_date": branch["target_date"],
        "facts": facts,
    }
    system = SYSTEM_PROMPT
    if initial_plan is not None:
        context["initial_plan"] = initial_plan
        context["answers"] = answers
        system = FINAL_PROMPT

    reply = await client.generate(
        system=system,
        prompt=json.dumps(context, ensure_ascii=False),
        json_output=True,
    )

    try:
        plan = ForkPlan.model_validate_json(reply.content)
    except ValidationError:
        raise ModelError(
            "MODEL_INVALID_OUTPUT", "模型返回的分叉方案格式不正确"
        ) from None

    fact_ids = {fact["id"] for fact in facts}
    references = (
        plan.preserved
        + plan.affected
        + plan.external_conditions
        + plan.information_limits
    )
    if any(item.fact_id not in fact_ids for item in references):
        raise ModelError(
            "MODEL_INVALID_OUTPUT", "分叉方案引用了资料快照之外的节点"
        )

    if initial_plan is not None:
        if plan.questions:
            raise ModelError(
                "MODEL_INVALID_OUTPUT", "整理后的方案不能追加问卷"
            )

        adopted = {
            item["assumption"]
            for item in answers
            if item["use_assumption"]
        }
        if not adopted.issubset(set(plan.assumptions)):
            raise ModelError(
                "MODEL_INVALID_OUTPUT", "最终方案遗漏或改写了已采用的假设"
            )

    return {
        "plan": plan.model_dump(),
        "model": reply.model,
        "usage": reply.usage,
    }