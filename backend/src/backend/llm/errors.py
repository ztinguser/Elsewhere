from openai import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APITimeoutError,
)

from backend.llm.client import ModelError


STATUS_ERRORS = {
    400: ("MODEL_REQUEST_INVALID", "模型请求参数不正确"),
    401: ("MODEL_AUTH_FAILED", "API Key 无效，请重新设置"),
    402: ("MODEL_BALANCE_LOW", "DeepSeek 账户余额不足"),
    403: ("MODEL_ACCESS_DENIED", "当前账户无权执行此请求"),
    429: ("MODEL_RATE_LIMITED", "模型请求过于频繁，请稍后重试"),
}


def model_error(exc: APIError) -> ModelError:
    if isinstance(exc, APITimeoutError):
        return ModelError("MODEL_TIMEOUT", "模型响应超时，请稍后重试")
    if isinstance(exc, APIConnectionError):
        return ModelError("MODEL_NETWORK_ERROR", "无法连接模型服务")
    if isinstance(exc, APIResponseValidationError):
        return ModelError("MODEL_INVALID_OUTPUT", "模型响应格式不正确")

    status = getattr(exc, "status_code", 0)
    if status >= 500:
        return ModelError("MODEL_UNAVAILABLE", "模型服务暂时不可用")

    code, message = STATUS_ERRORS.get(
        status, ("MODEL_REQUEST_FAILED", "模型请求失败，请检查模型配置")
    )
    return ModelError(code, message)