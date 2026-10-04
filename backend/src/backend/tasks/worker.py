import asyncio
import logging
from contextlib import suppress

from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.simulation.execution import execute_stage_task
from backend.storage.database import connect
from backend.storage.simulation_tasks import fail_stage_task
from backend.storage.task_queue import interrupt_pending
from backend.storage.tasks import get_task
from backend.tasks.fork import execute_fork_task


class TaskWorker:
    def __init__(self, path, credentials):
        self.path = path
        self.credentials = credentials
        self.wakeup = asyncio.Event()
        self.runner = None

    def start(self):
        with connect(self.path) as connection:
            interrupt_pending(connection)
        self.runner = asyncio.create_task(self.run())

    def notify(self):
        self.wakeup.set()

    async def close(self):
        with connect(self.path) as connection:
            interrupt_pending(connection)
        self.runner.cancel()
        with suppress(asyncio.CancelledError):
            await self.runner

    async def run(self):
        while True:
            await self.wakeup.wait()
            self.wakeup.clear()
            while True:
                with connect(self.path) as connection:
                    row = connection.execute(
                        "SELECT id FROM tasks WHERE status = 'queued' ORDER BY created_at, rowid LIMIT 1"
                    ).fetchone()
                    task = get_task(connection, row["id"]) if row else None
                if task is None:
                    break
                await self.execute(task)

    async def execute(self, task):
        client = None
        try:
            client = DeepSeekClient(self.credentials.require_key())
            if task["input_data"].get("operation") in ("fork_plan", "fork_answers"):
                await execute_fork_task(self.path, task, client)
            elif "position" in task["input_data"]:
                await execute_stage_task(self.path, task["id"], client)
            else:
                raise ModelError("TASK_UNSUPPORTED", "当前版本不支持此任务")
        except Exception as exc:
            code = exc.code if isinstance(exc, ModelError) else "TASK_EXECUTION_FAILED"
            message = str(exc) if isinstance(exc, ModelError) else "任务执行失败，请重试"
            with connect(self.path) as connection:
                current = get_task(connection, task["id"])
                if current["status"] in ("queued", "running"):
                    fail_stage_task(connection, task["id"], code=code, message=message,
                                    expected_status=current["status"])
            logging.getLogger("elsewhere").warning("task_id=%s error_code=%s", task["id"], code)
        finally:
            if client:
                try:
                    await client.aclose()
                except Exception:
                    logging.getLogger("elsewhere").warning("task_id=%s error_code=MODEL_CLOSE_FAILED", task["id"])
