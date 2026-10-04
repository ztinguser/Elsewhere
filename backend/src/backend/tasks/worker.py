import asyncio
import logging
from contextlib import suppress
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.llm.client import ModelError
from backend.llm.deepseek import DeepSeekClient
from backend.simulation.execution import execute_stage_task
from backend.storage.database import connect
from backend.storage.simulation_tasks import fail_stage_task
from backend.storage.task_queue import interrupt_pending
from backend.storage.tasks import WORKFLOW_VERSION, get_task
from backend.storage.task_recovery import reconcile_task, require_workflow_version
from backend.tasks.fork import execute_fork_task
from backend.tasks.workflow import TaskStopped, Workflow, checkpoint_version


class TaskWorker:
    def __init__(self, path, credentials, workflow_path=None):
        self.path = path
        self.credentials = credentials
        self.wakeup = asyncio.Event()
        self.runner = None
        self.workflow_path = workflow_path or path.with_name("workflow.sqlite")
        self.current_job = None
        self.current_id = None
        self.closed = False

    async def start(self):
        self.checkpoints = AsyncSqliteSaver.from_conn_string(str(self.workflow_path))
        self.saver = await self.checkpoints.__aenter__()
        try:
            await self.saver.setup()
            with connect(self.path) as connection:
                interrupt_pending(connection)
                rows = connection.execute("SELECT id FROM tasks WHERE status IN ('interrupted', 'waiting_input')").fetchall()
                for row in rows:
                    task = get_task(connection, row["id"])
                    if task["workflow_version"] == WORKFLOW_VERSION:
                        reconcile_task(connection, task)
            await self.sync_waits()
            self.runner = asyncio.create_task(self.run())
        except BaseException:
            await self.checkpoints.__aexit__(None, None, None)
            raise

    def notify(self):
        self.wakeup.set()

    async def close(self):
        if self.closed:
            return
        self.closed = True
        with connect(self.path) as connection:
            interrupt_pending(connection)
        self.runner.cancel()
        try:
            with suppress(asyncio.CancelledError):
                await self.runner
        finally:
            await self.checkpoints.__aexit__(None, None, None)

    def cancel(self, task_id):
        if self.current_id == task_id and self.current_job:
            self.current_job.cancel()

    async def require_version(self, task):
        require_workflow_version(task)
        saved = await self.saver.aget_tuple({"configurable": {"thread_id": task["id"]}})
        if saved and checkpoint_version(saved) != WORKFLOW_VERSION:
            raise ValueError("检查点版本不兼容，请使用对应版本的程序")

    async def sync_waits(self):
        with connect(self.path) as connection:
            rows = connection.execute("SELECT id FROM tasks WHERE status IN ('waiting_input', 'completed')").fetchall()
            tasks = [get_task(connection, row["id"]) for row in rows]
        for task in tasks:
            if task["workflow_version"] != WORKFLOW_VERSION:
                continue
            saved = await self.saver.aget_tuple({"configurable": {"thread_id": task["id"]}})
            if not saved and task["status"] == "completed":
                continue
            if saved and checkpoint_version(saved) != WORKFLOW_VERSION:
                continue
            async def no_work():
                pass
            await Workflow(self.path, task, self.saver).run(no_work)

    async def run(self):
        while True:
            await self.wakeup.wait()
            self.wakeup.clear()
            await self.sync_waits()
            while True:
                with connect(self.path) as connection:
                    row = connection.execute(
                        "SELECT id FROM tasks WHERE status = 'queued' ORDER BY created_at, rowid LIMIT 1"
                    ).fetchone()
                    task = get_task(connection, row["id"]) if row else None
                if task is None:
                    break
                self.current_id = task["id"]
                self.current_job = asyncio.create_task(self.execute(task))
                try:
                    await self.current_job
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                finally:
                    self.current_id = self.current_job = None

    async def execute(self, task):
        client = None
        try:
            try:
                await self.require_version(task)
            except ValueError as exc:
                raise ModelError("WORKFLOW_VERSION_UNSUPPORTED", str(exc)) from None
            client = DeepSeekClient(self.credentials.require_key())
            workflow = Workflow(self.path, task, self.saver)
            async def execute():
                if task["input_data"].get("operation") in ("fork_plan", "fork_answers"):
                    await execute_fork_task(self.path, task, client, workflow=workflow)
                elif "position" in task["input_data"]:
                    await execute_stage_task(self.path, task["id"], client, workflow=workflow)
                else:
                    raise ModelError("TASK_UNSUPPORTED", "当前版本不支持此任务")
            await workflow.run(execute)
        except TaskStopped:
            pass
        except Exception as exc:
            code = exc.code if isinstance(exc, ModelError) else "TASK_EXECUTION_FAILED"
            message = str(exc) if isinstance(exc, ModelError) else "任务执行失败，请重试"
            with connect(self.path) as connection:
                current = get_task(connection, task["id"])
                if current["status"] in ("queued", "running") and current["execution_id"] == task["execution_id"]:
                    fail_stage_task(connection, task["id"], code=code, message=message,
                                    expected_status=current["status"])
            logging.getLogger("elsewhere").warning("task_id=%s error_code=%s", task["id"], code)
        finally:
            if client:
                try:
                    await client.aclose()
                except Exception:
                    logging.getLogger("elsewhere").warning("task_id=%s error_code=MODEL_CLOSE_FAILED", task["id"])
