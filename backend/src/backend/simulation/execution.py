from pathlib import Path

from backend.llm.client import ModelClient, ModelError
from backend.models.simulation import StageData, StageReview
from backend.simulation.runner import run_stage
from backend.storage.database import connect
from backend.storage.simulation_context import build_simulation_context
from backend.storage.simulation_tasks import fail_stage_task
from backend.storage.stage_publication import publish_stage
from backend.storage.stages import get_stage
from backend.storage.tasks import get_task, update_task_status


async def execute_stage_task(
    path: Path,
    task_id: str,
    client: ModelClient,
) -> dict:
    with connect(path) as connection:
        task = get_task(connection, task_id)
        if (
            task is None
            or task["kind"] != "generate_branch"
            or "position" not in task["input_data"]
        ):
            raise ValueError("阶段任务不存在或类型不正确")
        claimed = update_task_status(
            connection, task_id,
            expected_status="queued", status="running", stage="simulation",
        )
        if not claimed:
            return get_task(connection, task_id)

    try:
        position = task["input_data"]["position"]
        with connect(path) as connection:
            existing = get_stage(connection, task["branch_id"], position)
            if existing is None:
                context = build_simulation_context(connection, task["branch_id"])
                if context["next_position"] != position:
                    raise ModelError("STAGE_STATE_CHANGED", "任务对应的阶段已经变化")

        if existing is None:
            result = await run_stage(client, context)

        with connect(path) as connection:
            completed = update_task_status(
                connection, task_id,
                expected_status="running", status="completed", stage="completed",
            )
            if not completed:
                return get_task(connection, task_id)
            if existing is None:
                publish_stage(
                    connection,
                    branch_id=task["branch_id"],
                    position=position,
                    data=StageData.model_validate(result["stage"]),
                    review=StageReview.model_validate(result["review"]),
                )
            return get_task(connection, task_id)

    except Exception as exc:
        code = exc.code if isinstance(exc, ModelError) else "STAGE_EXECUTION_FAILED"
        message = str(exc) if isinstance(exc, ModelError) else "阶段执行失败，请重试"
        with connect(path) as connection:
            fail_stage_task(connection, task_id, code=code, message=message)
        raise