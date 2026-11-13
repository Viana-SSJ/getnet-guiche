"""The model and the prompt helper, shared by the agents."""

import os
from datetime import date, timedelta

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from .guardrails import PROMPT_RULES

MODEL = os.getenv("AGENT_MODEL", "openrouter/deepseek/deepseek-v4-flash-0731")
FALLBACK_MODELS = [m for m in os.getenv("AGENT_FALLBACK_MODELS", "openai/gpt-oss-120b").split(",") if m]


def llm(model: str = MODEL) -> LiteLlm:
    """The model of an agent. OpenRouter tries the fallback models when the first one fails."""
    extra = {}
    if model.startswith("openrouter/") and FALLBACK_MODELS:
        extra["extra_body"] = {"models": [model.removeprefix("openrouter/"), *FALLBACK_MODELS]}
    return LiteLlm(model=model, num_retries=2, timeout=60, temperature=0.1, **extra)


def instruction(prompt: str):
    """Add the guardrail rules and today's date to a prompt."""
    def provide(_: ReadonlyContext) -> str:
        today = date.today()
        yesterday = today - timedelta(days=1)
        return f"{prompt}\n{PROMPT_RULES}\nToday is {today.isoformat()} ({today:%A}). Yesterday was {yesterday.isoformat()}."
    return provide
