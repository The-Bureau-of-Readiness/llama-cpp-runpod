"""
Runpod handler for processing jobs using LlamaCPP or OpenAI engines.
"""

from typing import Any
import os
import runpod

from utils import JobInput
from engine import LlamaCPPEngine, LlamaCPPOpenAIEngine

DEFAULT_MAX_CONCURRENCY = 8
max_concurrency = int(os.getenv("MAX_CONCURRENCY", DEFAULT_MAX_CONCURRENCY))

async def handler(job: Any):
    job_input = JobInput(job["input"])
    engine_class = LlamaCPPOpenAIEngine if job_input.openai_route else LlamaCPPEngine
    engine = engine_class()

    gen = engine.generate(job_input)
    async for batch in gen:
        yield batch

runpod.serverless.start(
    {
        "handler": handler,
        "concurrency_modifier": lambda _x: max_concurrency,
        "return_aggregate_stream": True,
    }
)
