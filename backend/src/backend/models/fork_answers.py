from pydantic import BaseModel, Field, model_validator


class ForkAnswer(BaseModel):
    question_id: str
    answer: str = ""
    use_assumption: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def require_one_choice(self):
        self.answer = self.answer.strip()
        if bool(self.answer) == self.use_assumption:
            raise ValueError("每题必须填写答案或明确采用假设，二者只能选择一个")
        return self


class ForkAnswersInput(BaseModel):
    expected_revision: int = Field(ge=1)
    answers: list[ForkAnswer] = Field(min_length=1, max_length=3)


def prepare_fork_answers(
    record: dict,
    data: ForkAnswersInput,
) -> list[dict]:
    if record["revision"] != data.expected_revision:
        raise ValueError("方案已变化，请重新读取后提交")

    if record["status"] != "waiting_input":
        raise ValueError("当前方案不在等待问卷回答")

    questions = record["initial_result"]["plan"]["questions"]
    expected_ids = [
        f"q{index}" for index in range(1, len(questions) + 1)
    ]
    answers = {item.question_id: item for item in data.answers}

    if (
        len(data.answers) != len(expected_ids)
        or set(answers) != set(expected_ids)
    ):
        raise ValueError("请完整回答原始问卷，题号不能重复或增加")

    result = []
    for question_id, question in zip(expected_ids, questions):
        item = answers[question_id]
        result.append({
            **item.model_dump(),
            "assumption": (
                question["assumption"] if item.use_assumption else None
            ),
        })
    return result