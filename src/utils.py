"""
This module contains utility classes and functions for handling job inputs.
"""


class JobInput:
    def __init__(self, job: dict):
        self.llm_input = job.get("messages", job.get("prompt"))
        self.stream = bool(job.get("stream", False))
        self.openai_route = job.get("openai_route")
        self.openai_input = job.get("openai_input")

        # Minimal validation for the common RunPod queue format.
        if self.openai_route is None and self.openai_input is None:
            if self.llm_input is None:
                raise ValueError("Input must include either 'prompt' (string) or 'messages' (list).")
