from backend.llm.client import ModelClient, ModelError
from backend.llm.simulation import generate_stage
from backend.llm.stage_review import review_stage
from backend.models.simulation import StageData, StageReview
from backend.simulation.rules import check_stage_rules


async def run_stage(client: ModelClient, context: dict, workflow=None) -> dict:
    draft = None
    issues = None
    calls = []

    for attempt in range(2):
        async def generate():
            return await generate_stage(client, context, draft=draft, issues=issues)

        generated = await workflow.step(f"simulation:{attempt}:write", generate) if workflow else await generate()
        data = StageData.model_validate(generated["stage"])
        rule_issues = check_stage_rules(data, context)
        async def check():
            return await review_stage(client, context, data)

        reviewed = await workflow.step(f"simulation:{attempt}:review", check) if workflow else await check()
        review = StageReview(
            issues=list(dict.fromkeys(rule_issues + reviewed["review"]["issues"]))
        )

        for kind, result in (("generate", generated), ("review", reviewed)):
            calls.append({
                "kind": kind,
                "model": result["model"],
                "usage": result["usage"],
            })

        if review.approved:
            return {
                "stage": data.model_dump(),
                "review": review.model_dump(),
                "audit": reviewed["audit"],
                "calls": calls,
            }

        draft = data.model_dump()
        issues = review.issues

    raise ModelError(
        "STAGE_REVIEW_FAILED",
        "当前阶段返工后仍未通过校验：" + "；".join(review.issues),
    )
