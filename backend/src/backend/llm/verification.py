import json

from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient


async def verify_model(api_key: str) -> dict:
    client = DeepSeekClient(api_key, max_tokens=64)
    try:
        reply = await client.generate(
            system="你正在执行接口连通性测试，请按要求返回 JSON。",
            prompt='请返回 {"ok": true}。',
            json_output=True,
        )
    finally:
        await client.aclose()

    if json.loads(reply.content).get("ok") is not True:
        raise ModelError("MODEL_INVALID_OUTPUT", "模型未返回预期的验证结果")

    return {
        "verified": True,
        "model": reply.model,
        "json_output": True,
        "usage": reply.usage,
    }