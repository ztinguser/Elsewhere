from pathlib import Path
from dataclasses import asdict
import json

from backend.llm.client import ModelClient, ModelError, ModelReply
from backend.llm.narrative import review_narrative, write_narrative
from backend.storage.database import connect
from backend.storage.narrative_context import build_narrative_context
from backend.storage.narratives import finish_narrative, get_narrative, get_narrative_attempt, save_narrative_draft
from backend.storage.stages import get_stage
from backend.storage.tasks import get_task, is_running, update_task_status
from backend.storage.task_events import record_event
from backend.models.narrative import NarrativeReview, NarrativeText


async def write_stage_narratives(path: Path, task_id: str, client: ModelClient, workflow=None) -> None:
    with connect(path) as connection:
        task = get_task(connection, task_id)
        if workflow and task["execution_id"] != workflow.task["execution_id"]:
            return
        branch_id, position = task["branch_id"], task["input_data"]["position"]
        stage = get_stage(connection, branch_id, position)
    kinds = ("chapter", "today", "retrospective") if stage["end_reason"] == "target" else ("chapter",)
    for kind in kinds:
        with connect(path) as connection:
            if not is_running(connection, task):
                return
            if get_narrative(connection, stage["id"], kind):
                continue
            context = build_narrative_context(connection, branch_id, position, kind)
            update_task_status(connection, task_id, expected_status="running",
                               status="running", stage=f"narrative:{kind}")
        draft, issues = None, None
        for attempt in range(2):
            async def generate():
                text, reply = await write_narrative(client, context, draft=draft, issues=issues)
                return {"text": text.model_dump(), "reply": asdict(reply)}

            name = f"{kind}:{attempt}"
            with connect(path) as connection:
                saved = get_narrative_attempt(connection, f"{task_id}:{name}")
            if saved:
                draft = NarrativeText(title=saved["title"], outline=json.loads(saved["outline"]),
                                      paragraphs=[p["content"] for p in saved["paragraphs"]])
                reply = ModelReply(content="", **json.loads(saved["generation"]))
            else:
                result = await workflow.step(f"{name}:write", generate) if workflow else await generate()
                draft, reply = NarrativeText(**result["text"]), ModelReply(**result["reply"])
            with connect(path) as connection:
                if not is_running(connection, task):
                    return
                version_id = save_narrative_draft(connection, branch_id, position, kind, draft, reply,
                                                 draft_key=f"{task_id}:{name}")

            async def review_text():
                review, reply = await review_narrative(client, context, draft)
                return {"review": review.model_dump(), "reply": asdict(reply)}

            if saved and saved["review"]:
                result = json.loads(saved["review"])
                review = NarrativeReview(**{key: result[key] for key in ("fidelity", "boundary", "style")})
                reply = ModelReply(content="", model=result["model"], usage=result["usage"])
            else:
                result = await workflow.step(f"{name}:review", review_text) if workflow else await review_text()
                review, reply = NarrativeReview(**result["review"]), ModelReply(**result["reply"])
            with connect(path) as connection:
                if not is_running(connection, task):
                    return
                changed = finish_narrative(connection, version_id, review, reply)
                if changed and not review.issues:
                    record_event(connection, task_id, "narrative_published",
                                 {"position": position, "kind": kind, "version_id": version_id})
            issues = review.issues
            if not issues:
                break
        else:
            raise ModelError("NARRATIVE_REVIEW_FAILED", "文学正文返工后仍未通过复核，请重试")
