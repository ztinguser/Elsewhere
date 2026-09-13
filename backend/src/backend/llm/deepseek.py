import asyncio
import json

from langchain.chat_models import init_chat_model
from langsmith import tracing_context
from openai import APIError

from backend.llm.client import ModelError, ModelReply
from backend.llm.errors import model_error


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "deepseek-v4-pro",
        timeout: float = 90,
        max_tokens: int = 4096,
    ):
        self.timeout = timeout
        self._model = init_chat_model(
            model=model,
            model_provider="deepseek",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=timeout,
            max_tokens=max_tokens,
            max_retries=2,
            extra_body={"thinking": {"type": "disabled"}},
        )

    async def generate(
        self, *, system: str, prompt: str, json_output: bool = False
    ) -> ModelReply:
        model = self._model
        if json_output:
            system += "\n请只返回一个 JSON 对象，不要添加 Markdown 标记。"
            model = model.bind(response_format={"type": "json_object"})

        try:
            with tracing_context(enabled=False):
                async with asyncio.timeout(self.timeout * 3):
                    reply = await model.ainvoke([
                        ("system", system),
                        ("human", prompt),
                    ])

            content = reply.content
            model_name = reply.response_metadata["model_name"]
            if reply.response_metadata.get("finish_reason") != "stop":
                raise ValueError
            if not isinstance(content, str) or not content.strip():
                raise ValueError
            if not isinstance(model_name, str) or not model_name:
                raise ValueError
            if json_output and not isinstance(json.loads(content), dict):
                raise ValueError

        except TimeoutError:
            raise ModelError("MODEL_TIMEOUT", "模型响应超时，请稍后重试") from None
        except APIError as exc:
            raise model_error(exc) from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ModelError(
                "MODEL_INVALID_OUTPUT", "模型返回内容为空、不完整或格式不正确"
            ) from None

        usage = None
        if reply.usage_metadata is not None:
            usage = {
                name: value
                for name, value in reply.usage_metadata.items()
                if type(value) is int
            }

        return ModelReply(content=content, model=model_name, usage=usage)