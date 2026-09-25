import json

from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.simulation import StageData, StageReview
from backend.prompts.stage_review import SYSTEM_PROMPT


async def review_stage(
    client: ModelClient,
    context: dict,
    data: StageData,
) -> dict:
    reply = await client.generate(
        system=SYSTEM_PROMPT,
        prompt=json.dumps(
            {"context": context, "stage": data.model_dump()},
            ensure_ascii=False,
        ),
        json_output=True,
    )

    try:
        review = StageReview.model_validate_json(reply.content)
    except ValidationError:
        raise ModelError(
            "MODEL_INVALID_OUTPUT", "模型返回的阶段评审格式不正确"
        ) from None

    return {
        "review": review.model_dump(),
        "model": reply.model,
        "usage": reply.usage,
    }