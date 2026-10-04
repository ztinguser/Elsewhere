from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context

from backend.llm.client import ModelError
from backend.storage.database import connect
from backend.storage.tasks import WORKFLOW_VERSION, get_task, is_running


class StepState(TypedDict, total=False):
    result: dict


class TaskState(TypedDict):
    task_id: str
    workflow_version: str


class TaskStopped(Exception):
    pass


def checkpoint_version(saved):
    values = saved.checkpoint["channel_values"]
    return values.get("workflow_version", values.get("__start__", {}).get("workflow_version"))


class Workflow:
    """任务图负责执行与等待；命名步骤各自保存结果，重放时不依赖调用顺序。"""

    def __init__(self, path, task, saver):
        self.path, self.task, self.saver = path, task, saver

    def check_running(self):
        with connect(self.path) as connection:
            if not is_running(connection, self.task):
                raise TaskStopped("本次执行已停止")

    async def step(self, name, action):
        self.check_running()

        async def execute(state):
            self.check_running()
            try:
                result = await action()
            except (ModelError, TaskStopped):
                raise
            except Exception:
                # 框架会保存节点错误，不把第三方异常中的凭据或请求体写入检查点。
                raise ModelError("TASK_EXECUTION_FAILED", "任务执行失败，请重试") from None
            self.check_running()
            return {"result": result}

        graph = StateGraph(StepState)
        graph.add_node("execute", execute)
        graph.add_edge(START, "execute")
        graph.add_edge("execute", END)
        graph = graph.compile(checkpointer=self.saver)
        config = {"configurable": {"thread_id": f"{self.task['id']}:{name}"}}
        with tracing_context(enabled=False):
            saved = await graph.aget_state(config)
            if saved.values and not saved.next:
                result = saved.values
            else:
                result = await graph.ainvoke(None if saved.created_at else {}, config, durability="sync")
        self.check_running()
        return result["result"]

    async def run(self, action):
        async def execute(state):
            with connect(self.path) as connection:
                current = get_task(connection, self.task["id"])
            if current["status"] in ("queued", "running"):
                try:
                    await action()
                except (ModelError, TaskStopped):
                    raise
                except Exception:
                    raise ModelError("TASK_EXECUTION_FAILED", "任务执行失败，请重试") from None
            return {}

        async def wait(state):
            with connect(self.path) as connection:
                current = get_task(connection, self.task["id"])
            if current["status"] == "waiting_input":
                interrupt({"reason": current["waiting_reason"],
                           "object_id": current["waiting_object_id"]})
            return {}

        graph = StateGraph(TaskState)
        graph.add_node("execute", execute)
        graph.add_node("wait", wait)
        graph.add_edge(START, "execute")
        graph.add_edge("execute", "wait")
        graph.add_edge("wait", END)
        graph = graph.compile(checkpointer=self.saver)
        config = {"configurable": {"thread_id": self.task["id"]}}
        with tracing_context(enabled=False):
            saved = await graph.aget_state(config)
            if saved.values and saved.values["workflow_version"] != WORKFLOW_VERSION:
                raise ModelError("WORKFLOW_VERSION_UNSUPPORTED", "检查点版本不兼容，请使用对应版本的程序")
            with connect(self.path) as connection:
                current = get_task(connection, self.task["id"])
            if (saved.next == ("wait",) and current["status"] == "waiting_input"
                    and any(item.interrupts for item in saved.tasks)):
                return
            if saved.created_at and not saved.next and current["status"] == "completed":
                return
            data = None if saved.next else {"task_id": self.task["id"], "workflow_version": WORKFLOW_VERSION}
            if saved.next == ("wait",) and current["status"] == "completed":
                # 用户输入已由业务接口提交，这里只结束旧图的等待，不作决定。
                data = Command(resume=True)
            await graph.ainvoke(data, config, durability="sync")
