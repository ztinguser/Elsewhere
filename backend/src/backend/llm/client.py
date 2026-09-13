from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelReply:
    """统一返回正文、实际响应中的模型标识、可获得的 token 用量"""
    content: str
    model: str
    usage: dict[str, int] | None = None


class ModelError(Exception):
    """统一失败形式"""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ModelClient(Protocol):
    """约定所有实现都提供相同的 generate() 方法"""
    async def generate(
        self, *, system: str, prompt: str, json_output: bool = False
    ) -> ModelReply:
        ...