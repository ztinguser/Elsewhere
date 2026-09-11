import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.api.errors import server_error

logger = logging.getLogger("elsewhere.http")


async def track_request(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    request.state.request_id = uuid4().hex
    started = perf_counter()
    error_type = "-"

    try:
        response = await call_next(request)
    except Exception as exc:
        error_type = type(exc).__name__
        response = await server_error(request, exc)

    response.headers["X-Request-ID"] = request.state.request_id

    level = logging.ERROR if response.status_code >= 500 else logging.INFO
    logger.log(
        level,
        "request_id=%s status=%s response_ready_ms=%.1f error_type=%s",
        request.state.request_id,
        response.status_code,
        (perf_counter() - started) * 1000,
        error_type,
    )
    return response