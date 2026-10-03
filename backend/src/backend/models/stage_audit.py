from pydantic import BaseModel, Field

from backend.models.simulation import StageReview


class ReviewCheck(StageReview):
    evidence: str = Field(min_length=1, pattern=r"\S")


class StageAudit(BaseModel):
    model_config = {"extra": "forbid"}

    decisions: ReviewCheck
    resources: ReviewCheck
    state: ReviewCheck

    def to_review(self) -> StageReview:
        checks = (self.decisions, self.resources, self.state)
        issues = [
            issue
            for check in checks
            for issue in check.issues
        ]
        return StageReview(issues=list(dict.fromkeys(issues)))