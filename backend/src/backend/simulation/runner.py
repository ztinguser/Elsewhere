from backend.llm.client import ModelClient, ModelError
from backend.llm.simulation import generate_stage
from backend.llm.stage_review import review_stage
from backend.models.simulation import StageData, StageReview
from backend.simulation.rules import check_stage_rules


async def run_stage(client: ModelClient, context: dict) -> dict:
    draft = None
    issues = None
    calls = []

    for _ in range(2):
        generated = await generate_stage(
            client, context, draft=draft, issues=issues,
        )
        data = StageData.model_validate(generated["stage"])
        rule_issues = check_stage_rules(data, context)
        reviewed = await review_stage(client, context, data)
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
                "calls": calls,
            }

        draft = data.model_dump()
        issues = review.issues

    raise ModelError(
        "STAGE_REVIEW_FAILED",
        "当前阶段返工后仍未通过校验：" + "；".join(review.issues),
    )