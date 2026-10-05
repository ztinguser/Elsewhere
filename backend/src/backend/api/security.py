from secrets import compare_digest

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.api.errors import error_response
from backend.api.session import SESSION_COOKIE

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

    if request.headers.get("sec-fetch-site") in ("cross-site", "same-site"):
        return error_response(403, "INVALID_ORIGIN", "不允许此请求来源")

    public = (request.method, request.url.path) in {
        ("GET", "/health"), ("POST", "/session"),
    }
    if not public:
        token = request.cookies.get(SESSION_COOKIE, "")
        if not compare_digest(token.encode(), request.app.state.session_token.encode()):
            return error_response(401, "SESSION_REQUIRED", "本地会话已失效，请重新连接")

    return await call_next(request)
