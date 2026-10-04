from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.data.archives import list_backups, make_archive, save_backup
from backend.data.deletion import delete_data, deletion_scope, stop_tasks
from backend.storage.database import connect


router = APIRouter(prefix="/data")


@router.get("")
def data_location(request: Request):
    directory = request.app.state.life_db.parent.resolve()
    return {"directory": str(directory), "life_database": str(directory / "life.sqlite"),
            "workflow_database": str(directory / "workflow.sqlite"),
            "backup_directory": str(directory / "backups"),
            "deletion_pending": (directory / "deletion.json").exists()}


@router.post("/export")
async def export_data(request: Request):
    state = request.app.state
    async with state.maintenance.exclusive(), state.maintenance.quiet_worker():
        content, _ = make_archive(state.life_db.parent, kind="export")
    return Response(content, media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="elsewhere-export.zip"'})


@router.post("/backups", status_code=201)
async def create_backup(request: Request):
    state = request.app.state
    async with state.maintenance.exclusive(), state.maintenance.quiet_worker():
        return save_backup(state.life_db.parent)


@router.get("/backups")
def read_backups(request: Request):
    return list_backups(request.app.state.life_db.parent)


@router.get("/backups/{backup_id}")
async def download_backup(backup_id: str, request: Request):
    directory = request.app.state.life_db.parent / "backups"
    # 仅接收应用实际列出的文件名，不把用户路径交给文件系统。
    if backup_id not in {item["id"] for item in list_backups(directory.parent)}:
        raise HTTPException(404, "备份不存在")
    return Response((directory / backup_id).read_bytes(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{backup_id}"'})


async def remove_data(request, branch_id=None):
    state = request.app.state
    async with state.maintenance.exclusive():
        with connect(state.life_db) as connection:
            scope = deletion_scope(connection, branch_id)
            if branch_id is not None and not scope["branches"]:
                raise HTTPException(404, "分支不存在")
            stop_tasks(connection, scope)
        for task_id in scope["tasks"]:
            state.worker.cancel(task_id)
        async with state.maintenance.quiet_worker():
            delete_data(state.life_db.parent, scope)
    return {"deleted_branches": len(scope["branches"]), "deleted_tasks": len(scope["tasks"])}


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str, request: Request):
    return await remove_data(request, branch_id)


@router.delete("")
async def clear_data(request: Request):
    return await remove_data(request)
