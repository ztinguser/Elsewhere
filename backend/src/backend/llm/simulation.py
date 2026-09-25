import json

from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.simulation import StageData
from backend.prompts.simulation import SYSTEM_PROMPT


async def generate_stage(
    client: ModelClient,
    context: dict,
    *,
    draft: dict | None = None,
    issues: list[str] | None = None,
) -> dict:
    if (draft is None) != (issues is None):
        raise ValueError("返工草稿和问题必须一起提供")

    payload = context.copy()
    if draft is not None:
        payload["draft"] = draft
        payload["issues"] = issues

    reply = await client.generate(
        system=SYSTEM_PROMPT,
        prompt=json.dumps(payload, ensure_ascii=False),
        json_output=True,
    )

    try:
        stage = StageData.model_validate_json(reply.content)
    except ValidationError:
        raise ModelError(
            "MODEL_INVALID_OUTPUT", "模型返回的阶段推演格式不正确"
        ) from None

    return {
        "stage": stage.model_dump(),
        "model": reply.model,
        "usage": reply.usage,
    }