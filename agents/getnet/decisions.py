"""Ask a decision model (the OpenRouter Decisions API): typed answers with a probability, for about US$ 0.000005.

A decision model reads a text (`state`) and answers fixed questions: yes or no (`noul`), or one of some
options (`choice`). It does not write text and does not search the web.
"""

import os

import httpx

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.getenv("DECISION_MODEL", "microsoft/microsoft-decision-1")


def _request(state: str, questions: dict) -> dict:
    return {"url": URL, "headers": {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            "json": {"model": MODEL, "state": state, "questions": questions}}


def decide(state: str, questions: dict, timeout: float = 60) -> dict:
    response = httpx.post(**_request(state, questions), timeout=timeout)
    response.raise_for_status()
    return response.json()["answers"]


async def adecide(state: str, questions: dict, timeout: float = 15) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(**_request(state, questions))
    response.raise_for_status()
    return response.json()["answers"]
