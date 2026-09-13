from backend.llm.client import ModelError, ModelReply


class FakeModel:
    def __init__(self, result: ModelReply | ModelError):
        self.result = result

    async def generate(
        self, *, system: str, prompt: str, json_output: bool = False
    ) -> ModelReply:
        if isinstance(self.result, ModelError):
            raise self.result
        return self.result