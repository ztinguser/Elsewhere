import json

from pydantic import ValidationError

from backend.llm.client import ModelClient, ModelError
from backend.models.narrative import NarrativeReview, NarrativeText
from backend.prompts.narrative import REVIEW_PROMPT, WRITE_PROMPT


async def write_narrative(client: ModelClient, context: dict, *, draft=None, issues=None):
    payload = {"context": context}
    if draft is not None:
        payload.update(draft=draft.model_dump(), issues=issues)
    reply = await client.generate(
        system=WRITE_PROMPT, prompt=json.dumps(payload, ensure_ascii=False), json_output=True,
    )
    try:
        return NarrativeText.model_validate_json(reply.content), reply
    except ValidationError:
        raise ModelError("MODEL_INVALID_OUTPUT", "模型返回的文学正文格式不正确") from None


async def review_narrative(client: ModelClient, context: dict, draft: NarrativeText):
    reply = await client.generate(
        system=REVIEW_PROMPT,
        prompt=json.dumps({"context": context, "draft": draft.model_dump()}, ensure_ascii=False),
        json_output=True,
    )
    try:
        return NarrativeReview.model_validate_json(reply.content), reply
    except ValidationError:
        raise ModelError("MODEL_INVALID_OUTPUT", "模型返回的叙事复核格式不正确") from None
