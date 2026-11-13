"""Change one part of the design at a time, run the dev set, and compare with the real design.

    uv run python -m evals.ablations [--set evals/hard.jsonl] [baseline single-agent no-history free-search wrong-number router-replies]

Each variant is built here from the same parts as the app, so the app has no switch for experiments.
The variants with other models per agent (cheaper specialists, the fastest providers) were tried and
not kept; their results are in evals/results/.
"""

import asyncio
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

load_dotenv()  # before the agents read AGENT_MODEL

from agents.getnet import agent as getnet  # noqa: E402
from agents.getnet import knowledge, reply, router, support  # noqa: E402
from agents.getnet.common import instruction, llm  # noqa: E402
from agents.getnet.evidence import CALLBACKS  # noqa: E402
from agents.getnet.tools.customer import get_receivables, get_recent_transactions, get_terminal_status  # noqa: E402
from agents.getnet.tools.handoff import create_ticket  # noqa: E402
from agents.getnet.tools.kb_search import search_kb  # noqa: E402
from agents.getnet.tools.web import get_exchange_rate, get_weather, web_search  # noqa: E402
from evals.run import main as run_set  # noqa: E402

DEV = Path("evals/dev.jsonl")
ROUTER_INTERNAL_ANSWER = """Then write an internal answer for the reply agent, which writes to the merchant: every fact, number,
date, step, ticket number and source that the tools gave you. Write it in the language of the
merchant's message, even when the tools answered in Portuguese. Getnet names and Portuguese terms
inside an English sentence do not make it Portuguese."""
ROUTER_REPLY = """Then write the reply to the merchant, and only the reply: it goes to the merchant as it is. Write
it in the language of the merchant's message, even when the tools answered in Portuguese: judge the
language by the grammar of the sentence; Getnet names and Portuguese terms inside an English sentence
do not make it Portuguese. Give every fact, number, date, step, ticket number and source that the
tools gave you, and add no fact. Be short, clear and friendly: numbered steps for instructions, a
short list for comparisons. End with the sources, if the tools gave any."""
RESULTS = Path("evals/results")
# The knowledge prompt before its searches had a limit: "search again with other words".
FREE_SEARCH = knowledge.PROMPT.replace(
    "To compare two products, search each one. Make the\n   searches that you need in one step: you can call search_kb several times at once. Search at most\n   3 times in all; then answer with what you found.",
    "Search again with other words if the results do not\n   answer. To compare two products, search each one.")


def single_agent() -> Agent:
    """One agent with every tool and every prompt: no agent tools."""
    prompt = (router.PROMPT.split("The agent tools:")[0] + "\nYour tools answer about products and the web:\n"
              + knowledge.PROMPT + "\nand about the merchant's own account:\n" + support.PROMPT)
    return Agent(name="router", description="Answers a merchant message with its tools.", model=llm(),
                 instruction=instruction(prompt), **CALLBACKS,
                 tools=[search_kb, web_search, get_weather, get_exchange_rate, get_receivables, get_terminal_status,
                        get_recent_transactions, create_ticket])


def free_search() -> Agent:
    assert FREE_SEARCH != knowledge.PROMPT, "the knowledge prompt changed: update FREE_SEARCH"
    free = knowledge.agent.model_copy(update={"instruction": instruction(FREE_SEARCH)})
    tools = [t for t in support.agent.tools if not isinstance(t, AgentTool)] + [AgentTool(free, include_plugins=False)]
    return router.make_router([free, support.agent.model_copy(update={"tools": tools})])


def router_replies() -> Agent:
    """The router writes to the merchant: no reply agent, so one long text fewer for each message."""
    prompt = router.PROMPT.replace(ROUTER_INTERNAL_ANSWER, ROUTER_REPLY)
    assert prompt != router.PROMPT, "the router prompt changed: update ROUTER_INTERNAL_ANSWER"
    return router.make_router(getnet.AGENT_TOOLS).model_copy(update={"instruction": instruction(prompt + "\n".join(
        f"- {a.name}: {a.description}" for a in getnet.AGENT_TOOLS))})


def wrong_number(agent: Agent) -> Agent:
    """The reply agent, with 7 added to the first number of its first reply to each message: a fault for the check."""
    done = set()

    def corrupt(callback_context, llm_response):
        key = (callback_context.session.id, callback_context.state.get("message"))
        parts = llm_response.content.parts if llm_response.content else []
        text = "".join(p.text or "" for p in parts)
        if key in done or not (match := re.search(r"\d+", text)):
            return None
        done.add(key)
        wrong = text[:match.start()] + str(int(match.group()) + 7) + text[match.end():]
        return llm_response.model_copy(update={"content": types.Content(role="model", parts=[types.Part(text=wrong)])})

    return agent.model_copy(update={"after_model_callback": corrupt})


VARIANTS = {
    "baseline": lambda: router.make_router(getnet.AGENT_TOOLS),
    "single-agent": single_agent,
    "no-history": lambda: router.make_router(getnet.AGENT_TOOLS),  # guard reads HISTORY_TURNS = 0
    "free-search": free_search,
    "wrong-number": lambda: router.make_router(getnet.AGENT_TOOLS),  # with wrong_number(reply.agent)
    "router-replies": router_replies,  # with no reply agent
}


def usage() -> float:
    """The money spent so far with the OpenRouter key (it updates a few seconds after a call)."""
    response = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
    return response.json()["data"]["usage"]


async def ablate(name: str, cases: Path = DEV) -> dict:
    getnet.HISTORY_TURNS = 0 if name == "no-history" else 10
    writer = {"wrong-number": wrong_number(reply.agent), "router-replies": None}.get(name, reply.agent)
    app = getnet.make_app(VARIANTS[name](), writer)
    sessions = SqliteSessionService(str(Path(tempfile.mkdtemp()) / "ablation.db"))
    suffix = "" if cases == DEV else f"-{cases.stem}"
    before = usage()
    await run_set(cases, again=False, runner=Runner(app=app, session_service=sessions), name=f"ablation-{name}{suffix}")
    await asyncio.sleep(60)  # the key's usage updates late
    path = sorted(RESULTS.glob(f"ablation-{name}{suffix}-2*.json"))[-1]
    data = json.loads(path.read_text())
    data["summary"]["cost_usd"] = round(usage() - before, 4)  # one run at a time, or the cost mixes runs
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data["summary"]


if __name__ == "__main__":
    args = sys.argv[1:]
    cases = Path(args.pop(args.index("--set") + 1)) if "--set" in args else DEV
    for variant in [a for a in args if a != "--set"] or list(VARIANTS):
        asyncio.run(ablate(variant, cases))
