def public_fork_plan(record: dict) -> dict:
    initial_plan = record["initial_result"]["plan"]
    result = record["final_result"] or record["initial_result"]
    plan = result["plan"]

    return {
        "branch_id": record["branch_id"],
        "revision": record["revision"],
        "status": record["status"],
        "plan": {
            field: plan[field]
            for field in (
                "change",
                "preserved",
                "affected",
                "external_conditions",
                "information_limits",
                "assumptions",
                "blockers",
            )
        },
        "questions": [
            {
                "question_id": f"q{index}",
                "question": question["question"],
                "assumption": question["assumption"],
            }
            for index, question in enumerate(
                initial_plan["questions"], start=1
            )
        ],
        "answers": record["answers"],
    }