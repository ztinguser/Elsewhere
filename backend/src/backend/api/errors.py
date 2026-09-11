from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    response = error_response(
        exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail)
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "请求参数不符合要求")


async def server_error(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "服务暂时无法完成请求")