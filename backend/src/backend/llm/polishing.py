from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.polishing import PolishResult
from backend.prompts.polishing import SYSTEM_PROMPT


async def polish_text(client: ModelClient, content: str) -> dict:
    reply = await client.generate(
        system=SYSTEM_PROMPT,
        prompt=content,
        json_output=True,
    )
    try:
        result = PolishResult.model_validate_json(reply.content)
    except ValidationError:
        raise ModelError(
            "MODEL_INVALID_OUTPUT", "模型返回的润色结果格式不正确"
        ) from None

    return {
        **result.model_dump(),
        "model": reply.model,
        "usage": reply.usage,
    }