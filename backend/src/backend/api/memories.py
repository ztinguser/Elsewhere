from fastapi import APIRouter, HTTPException, Request

from backend.models.memories import MemoryInput
from backend.storage.database import connect
from backend.storage.memories import create_memory, get_memory


router = APIRouter(prefix="/memories")


@router.post("", status_code=201)
def add_memory(data: MemoryInput, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        result = create_memory(connection, data)
    return result


@router.get("/{memory_id}")
def read_memory(memory_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        memory = get_memory(connection, memory_id)

    if memory is None:
        raise HTTPException(404, "回忆不存在")

    return memory