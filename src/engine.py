import json
from typing import AsyncGenerator, Dict, Any, Optional

from openai import OpenAI
from utils import JobInput

client = OpenAI(
    base_url="http://localhost:3098/v1/",
    api_key="none",
)

_cached_model_id: Optional[str] = None


def get_default_model_id() -> str:
    global _cached_model_id
    if _cached_model_id is None:
        models = client.models.list().data
        if not models:
            raise RuntimeError("No models returned by llama-server /v1/models")
        _cached_model_id = models[0].id
    return _cached_model_id


class LlamaCPPOpenAIEngine:
    async def generate(self, job_input: JobInput):
        openai_input = job_input.openai_input

        if job_input.openai_route == "/v1/models":
            async for response in self._handle_model_request():
                yield response
            return

        if job_input.openai_route in ("/v1/chat/completions", "/v1/completions"):
            async for response in self._handle_chat_or_completion_request(
                openai_input,
                chat=(job_input.openai_route == "/v1/chat/completions"),
            ):
                yield response
            return

        yield {"error": "invalid route"}

    async def _handle_model_request(self):
        try:
            response = client.models.list()
            yield {
                "object": "list",
                "data": [model.to_dict() for model in response.data],
            }
        except Exception as e:
            yield {"error": str(e)}

    async def _handle_chat_or_completion_request(self, openai_input: Dict[str, Any], chat: bool = False):
        try:
            if chat:
                response = client.chat.completions.create(**openai_input)
            else:
                response = client.completions.create(**openai_input)

            if not openai_input.get("stream", False):
                yield response.to_dict()
                return

            for chunk in response:
                yield "data: " + json.dumps(chunk.to_dict(), separators=(",", ":")) + "\n\n"

            yield "data: [DONE]"

        except Exception as e:
            yield {"error": str(e)}


class LlamaCPPEngine:
    """
    Front adapter: normalizes prompt vs chat into OpenAI-form requests to the local llama-server.
    """
    def __init__(self):
        self._openai_engine = LlamaCPPOpenAIEngine()

    async def generate(self, job_input: JobInput):
        model = get_default_model_id()

        if isinstance(job_input.llm_input, str):
            openai_job = JobInput(
                {
                    "openai_route": "/v1/completions",
                    "openai_input": {
                        "model": model,
                        "prompt": job_input.llm_input,
                        "stream": job_input.stream,
                    },
                }
            )
        else:
            openai_job = JobInput(
                {
                    "openai_route": "/v1/chat/completions",
                    "openai_input": {
                        "model": model,
                        "messages": job_input.llm_input,
                        "stream": job_input.stream,
                    },
                }
            )

        gen = self._openai_engine.generate(openai_job)
        async for batch in gen:
            yield batch
