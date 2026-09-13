from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, SecretStr

from backend.api.errors import error_response
from backend.llm.client import ModelError
from backend.llm.verification import verify_model


router = APIRouter(prefix="/model")


class KeyInput(BaseModel):
    key: SecretStr
    remember: bool = False


@router.get("/credentials")
async def get_credentials(request: Request) -> dict:
    return request.app.state.credentials.status()


@router.put("/credentials")
async def set_credentials(data: KeyInput, request: Request) -> dict:
    store = request.app.state.credentials
    try:
        store.set_key(
            data.key.get_secret_value(),
            remember=data.remember,
        )
    except ValueError:
        raise HTTPException(422, "API Key 不能为空") from None
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    return store.status()


@router.delete("/credentials")
async def clear_credentials(request: Request) -> dict:
    store = request.app.state.credentials
    try:
        store.clear()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    return store.status()


@router.post("/verify")
async def verify_credentials(request: Request):
    try:
        key = request.app.state.credentials.require_key()
        return await verify_model(key)
    except ModelError as exc:
        status = 400 if exc.code == "MODEL_KEY_REQUIRED" else 502
        return error_response(status, exc.code, str(exc))