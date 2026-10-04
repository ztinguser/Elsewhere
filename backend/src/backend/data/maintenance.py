import asyncio
from contextlib import asynccontextmanager

from fastapi import HTTPException

from backend.api.errors import error_response


class Maintenance:
    def __init__(self, worker):
        self.worker = worker
        self.active = False
        self.writes = 0
        self.idle = asyncio.Event()
        self.idle.set()
        self.timeout = 5

    @asynccontextmanager
    async def exclusive(self):
        if self.active:
            raise HTTPException(409, "另一项数据管理操作尚未完成")
        self.active = self.worker.paused = True
        try:
            try:
                await asyncio.wait_for(self.idle.wait(), self.timeout)
            except TimeoutError:
                raise HTTPException(409, "仍有保存请求未结束，请稍后重试") from None
            yield
        finally:
            pending = (self.worker.path.parent / "deletion.json").exists()
            self.active = self.worker.paused = pending
            if not pending:
                self.worker.notify()

    @asynccontextmanager
    async def quiet_worker(self):
        try:
            await asyncio.wait_for(self.worker.activity.acquire(), self.timeout)
        except TimeoutError:
            raise HTTPException(409, "生成任务尚未停止，请等待完成或取消后重试") from None
        try:
            yield
        finally:
            self.worker.activity.release()


async def protect_writes(request, call_next):
    manager = request.app.state.maintenance
    if (request.method in ("GET", "HEAD", "OPTIONS")
            or request.url.path == "/data" or request.url.path.startswith("/data/")):
        return await call_next(request)
    if manager.active:
        return error_response(503, "DATA_MAINTENANCE", "正在管理本地数据，请稍后重试保存")
    manager.writes += 1
    manager.idle.clear()
    try:
        return await call_next(request)
    finally:
        manager.writes -= 1
        if not manager.writes:
            manager.idle.set()
