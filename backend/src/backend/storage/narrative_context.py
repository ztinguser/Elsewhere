from backend.storage.branches import get_branch
from backend.storage.fork_plans import get_fork_plan
from backend.storage.narratives import get_narrative, require_chapters
from backend.storage.stages import get_stage_detail, list_stages
from backend.storage.versions import get_fact_version


def build_narrative_context(connection, branch_id: str, position: int, kind: str) -> dict:
    branch = get_branch(connection, branch_id)
    current = get_stage_detail(connection, branch_id, position)
    if branch is None or current is None:
        raise ValueError("分支或阶段不存在")
    if kind != "chapter" and current["end_reason"] != "target":
        raise ValueError("尚未抵达固定终点")
    require_chapters(connection, branch_id, position - 1 if kind == "chapter" else position)
    record = get_fork_plan(connection, branch_id)
    if record is None or record["status"] != "confirmed":
        raise ValueError("分叉方案尚未确认")
    plan = (record["final_result"] or record["initial_result"])["plan"]
    facts = {branch["fork_fact_id"]}
    for field in ("preserved", "affected", "external_conditions", "information_limits"):
        facts.update(item["fact_id"] for item in plan[field])
    history = []
    previous_chapter = None
    for stage in list_stages(connection, branch_id):
        if stage["position"] > position:
            break
        detail = get_stage_detail(connection, branch_id, stage["position"])
        events = [event["data"] for event in detail["events"]]
        for event in events:
            facts.update(event["fact_ids"])
        choice = detail["choice"]
        item = {
            "position": stage["position"], "end_time_text": stage["end_time_text"],
            "end_reason": stage["end_reason"], "events": events,
            "choice": choice["data"] if choice else None,
        }
        # 补写旧章节时，当前节点后来提交的决定也不能提前进入正文。
        if stage["position"] < position:
            if choice is None or not choice["decision"]:
                raise ValueError("历史阶段存在未提交的决定")
            item["decision"] = choice["decision"]
            previous_chapter = get_narrative(connection, stage["id"], "chapter")
        history.append(item)
    snapshot = get_fact_version(connection, branch["fact_version_id"])
    return {
        "kind": kind, "position": position, "target_date": branch["target_date"],
        "alternative": branch["alternative"],
        "plan": {key: value for key, value in plan.items() if key not in ("questions", "blockers")},
        "facts": [
            {"id": fact["id"], "time_text": fact.get("time_text"), "content": fact["content"]}
            for fact in snapshot["facts"] if fact["id"] in facts
        ],
        "stages": history,
        "previous_chapter": {
            "title": previous_chapter["title"],
            "paragraphs": [p["content"] for p in previous_chapter["paragraphs"]],
        } if previous_chapter and kind == "chapter" else None,
    }
