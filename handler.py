"""
Runpod Hub scanner entrypoint.

The actual implementation lives in src/handler.py.
This file exists so Runpod's GitHub-repo scanner can detect the handler.
"""
from src.handler import handler  # noqa: F401
import runpod

# Start the serverless worker using the handler from src/handler.py
runpod.serverless.start(
    {
        "handler": handler,
        "concurrency_modifier": lambda _x: int(__import__("os").environ.get("MAX_CONCURRENCY", "8")),
        "return_aggregate_stream": True,
    }
)
