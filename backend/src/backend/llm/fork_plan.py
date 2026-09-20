import json

from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.fork_plan import ForkPlan
from backend.prompts.fork_plan import SYSTEM_PROMPT


async def generate_fork_plan(
    client: ModelClient,
    branch: dict,
    snapshot: dict,
) -> dict:
    """根据分支绑定的资料快照生成初始分叉方案，并检查输出结构与节点引用。

        Args:
            client: 模型调用客户端，由调用方负责创建和关闭。
            branch: 已保存的分支，包含分叉节点、替代决定和整体推演终点。
            snapshot: 该分支绑定的固定事实快照，其中 facts 保存回忆列表。

        Returns:
            包含 plan、model 和 usage 的字典，分别为分叉方案、
            实际响应模型标识和可获得的用量。plan 包含内部提问理由，
            不能直接作为面向页面的响应。

        Raises:
            ModelError: 模型调用失败、输出结构不正确，或引用了快照之外的节点。
        """
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

    reply = await client.generate(
        system=SYSTEM_PROMPT,
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

    return {
        "plan": plan.model_dump(),
        "model": reply.model,
        "usage": reply.usage,
    }