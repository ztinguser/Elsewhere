import asyncio
import json

from fastapi import APIRouter, Header, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from backend.api.simulation_read import read_task
from backend.storage.branches import get_branch
from backend.storage.database import connect
from backend.storage.task_events import list_events
from backend.storage.tasks import get_task


router = APIRouter(prefix="/branches")


@router.get("/{branch_id}/tasks")
def read_tasks(branch_id: str, request: Request):
    with connect(request.app.state.life_db) as connection:
        if get_branch(connection, branch_id) is None:
            raise HTTPException(404, "分支不存在")
        rows = connection.execute(
            "SELECT id FROM tasks WHERE branch_id = ? ORDER BY created_at, rowid", (branch_id,)
        ).fetchall()
        return [get_task(connection, row["id"]) for row in rows]


@router.get("/{branch_id}/tasks/{task_id}/events")
async def task_events(branch_id: str, task_id: str, request: Request,
                      after: int = Query(default=0, ge=0),
                      last_event_id: str | None = Header(default=None)):
    read_task(branch_id, task_id, request)
    try:
        cursor = int(last_event_id) if last_event_id is not None else after
        if cursor < 0:
            raise ValueError
    except ValueError:
        raise HTTPException(400, "事件序号必须是非负整数") from None

    async def stream():
        nonlocal cursor
        idle = 0
        while not await request.is_disconnected():
            with connect(request.app.state.life_db) as connection:
                events = list_events(connection, task_id, cursor)
                task = get_task(connection, task_id)
            if task is None:
                yield f'event: deleted\ndata: {json.dumps({"id": task_id, "branch_id": branch_id})}\n\n'
                return
            for event in events:
                cursor = event["seq"]
                yield f"id: {cursor}\nevent: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            if len(events) == 100:
                continue
            if task["status"] not in ("queued", "running"):
                # 即使客户端游标超前或已追平，也能拿到最终状态及等待原因。
                public = {key: task[key] for key in (
                    "id", "branch_id", "status", "stage", "waiting_reason",
                    "waiting_object_id", "error_code", "error_message", "updated_at",
                )}
                yield f"event: snapshot\ndata: {json.dumps(public, ensure_ascii=False)}\n\n"
                return
            idle += 1
            if idle % 30 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
