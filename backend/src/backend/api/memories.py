from fastapi import APIRouter, HTTPException, Query, Request, Response
from backend.models.memories import MemoryInput, MemoryOrder, MemoryUpdate
from backend.storage.memory_order import reorder_memories
from backend.storage.database import connect
from backend.storage.memories import (
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    update_memory,
)

router = APIRouter(prefix="/memories")


@router.post("", status_code=201)
def add_memory(data: MemoryInput, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        result = create_memory(connection, data)
    return result


@router.get("")
def read_memories(request: Request, q: str = "") -> list[dict]:
    with connect(request.app.state.life_db) as connection:
        return list_memories(connection, query=q)


@router.get("/{memory_id}")
def read_memory(memory_id: str, request: Request) -> dict:
    with connect(request.app.state.life_db) as connection:
        memory = get_memory(connection, memory_id)

    if memory is None:
        raise HTTPException(404, "回忆不存在")

    return memory


@router.put("/order", status_code=204)
def save_memory_order(data: MemoryOrder, request: Request) -> Response:
    try:
        with connect(request.app.state.life_db) as connection:
            reorder_memories(connection, data.ids)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return Response(status_code=204)


@router.put("/{memory_id}")
def edit_memory(
    memory_id: str, data: MemoryUpdate, request: Request
) -> dict:
    try:
        with connect(request.app.state.life_db) as connection:
            result = update_memory(
                connection,
                memory_id,
                data,
                expected_revision=data.expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return result


@router.delete("/{memory_id}", status_code=204)
def remove_memory(
    memory_id: str,
    request: Request,
    expected_revision: int = Query(ge=1),
) -> Response:
    try:
        with connect(request.app.state.life_db) as connection:
            delete_memory(
                connection,
                memory_id,
                expected_revision=expected_revision,
            )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None

    return Response(status_code=204)