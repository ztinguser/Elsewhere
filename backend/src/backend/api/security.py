from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.api.errors import error_response

LOCAL_HOST = "127.0.0.1:8000"
LOCAL_ORIGIN = f"http://{LOCAL_HOST}"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def check_source(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    if request.headers.get("host") != LOCAL_HOST:
        return error_response(400, "INVALID_HOST", "不允许访问此主机")

    origin = request.headers.get("origin")
    if origin is not None and origin != LOCAL_ORIGIN:
        return error_response(403, "INVALID_ORIGIN", "不允许此请求来源")

    if request.method not in SAFE_METHODS and origin is None:
        return error_response(403, "ORIGIN_REQUIRED", "写请求必须提供来源")

    return await call_next(request)