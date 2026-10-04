from pathlib import Path

from backend.llm.client import ModelClient, ModelError
from backend.llm.narrative import review_narrative, write_narrative
from backend.storage.database import connect
from backend.storage.narrative_context import build_narrative_context
from backend.storage.narratives import finish_narrative, get_narrative, save_narrative_draft
from backend.storage.stages import get_stage
from backend.storage.tasks import get_task, update_task_status
from backend.storage.task_events import record_event


async def write_stage_narratives(path: Path, task_id: str, client: ModelClient) -> None:
    with connect(path) as connection:
        task = get_task(connection, task_id)
        branch_id, position = task["branch_id"], task["input_data"]["position"]
        stage = get_stage(connection, branch_id, position)
    kinds = ("chapter", "today", "retrospective") if stage["end_reason"] == "target" else ("chapter",)
    for kind in kinds:
        with connect(path) as connection:
            if get_task(connection, task_id)["status"] != "running":
                return
            if get_narrative(connection, stage["id"], kind):
                continue
            context = build_narrative_context(connection, branch_id, position, kind)
            update_task_status(connection, task_id, expected_status="running",
                               status="running", stage=f"narrative:{kind}")
        draft, issues = None, None
        for attempt in range(2):
            draft, reply = await write_narrative(client, context, draft=draft, issues=issues)
            with connect(path) as connection:
                if get_task(connection, task_id)["status"] != "running":
                    return
                version_id = save_narrative_draft(connection, branch_id, position, kind, draft, reply)
            review, reply = await review_narrative(client, context, draft)
            with connect(path) as connection:
                if get_task(connection, task_id)["status"] != "running":
                    return
                finish_narrative(connection, version_id, review, reply)
                if not review.issues:
                    record_event(connection, task_id, "narrative_published",
                                 {"position": position, "kind": kind, "version_id": version_id})
            issues = review.issues
            if not issues:
                break
        else:
            raise ModelError("NARRATIVE_REVIEW_FAILED", "文学正文返工后仍未通过复核，请重试")
