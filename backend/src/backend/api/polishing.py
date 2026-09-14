from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.llm.polishing import polish_text
from backend.models.polishing import PolishInput


router = APIRouter(prefix="/memories")


@router.post("/polish")
async def polish_memory(data: PolishInput, request: Request):
    try:
        key = request.app.state.credentials.require_key()
        client = DeepSeekClient(key)
        try:
            result = await polish_text(client, data.content)
        finally:
            await client.aclose()
    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))

    return JSONResponse(
        content=result,
        media_type="application/json; charset=utf-8",
    )