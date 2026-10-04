from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from backend.models.stage_audit import ReviewCheck


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class NarrativeText(BaseModel):
    model_config = {"extra": "forbid"}

    title: Text
    outline: list[Text] = Field(min_length=1)
    paragraphs: list[Text] = Field(min_length=1)


class NarrativeReview(BaseModel):
    model_config = {"extra": "forbid"}

    fidelity: ReviewCheck
    boundary: ReviewCheck
    style: ReviewCheck

    @property
    def issues(self) -> list[str]:
        return list(dict.fromkeys(
            issue for check in (self.fidelity, self.boundary, self.style)
            for issue in check.issues
        ))
