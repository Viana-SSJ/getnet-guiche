"""POST /chat: run the ADK app for one message of a conversation, check the answer, and open a ticket if anything fails."""

import json
import logging
import time
import uuid
from contextlib import suppress
from dataclasses import asdict, dataclass, field

from google.adk.agents.run_config import RunConfig
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types
from opentelemetry import metrics, trace

from . import evidence, guardrails, notify, store, tagger
from .agent import app
from .common import MODEL
from .guardrails import mask_sensitive
from .router import PROMPT as ROUTER_PROMPT
from .tools import handoff

log = logging.getLogger("chat")
tracer = trace.get_tracer("getnet.chat")
meter = metrics.get_meter("getnet.chat")
REQUESTS = meter.create_counter("chat.requests", unit="1", description="Merchant messages, by agents used, tag and fallback")
LATENCY = meter.create_histogram("chat.latency", unit="ms", description="Time to answer one merchant message")
TOOL_CALLS = meter.create_counter("chat.tool_calls", unit="1", description="Tool calls, by calling agent and kind: run, repeat, blocked")
# A last stop for a run that loops; the tool call limit of each agent (common.py) comes first.
RUN_CONFIG = RunConfig(max_llm_calls=50)
# When the check stops an answer, the flow runs once more and the router learns why (agent.guard).
REPLANS = 1
# Above this P(injection), the answer is not sent and a person takes over. Split conformal on normal messages,
# so that at most 1 % of them goes to a person (evals/injection.py, which also measures the attacks it stops).
INJECTION_LIMIT = 0.3208
# The messages that a session keeps. Each history change is an event that stores the whole list, so an
# unbounded list grows as the square of the conversation. The router reads fewer (agent.HISTORY_TURNS).
KEEP_MESSAGES = 40


class SessionNotFound(Exception):
    """No conversation with this id for this merchant."""


@dataclass
class ChatResponse:
    answer: str = ""
    tag: str = "other"
    tag_confidence: float | None = None
    agents_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    handoff: bool = False
    ticket: str | None = None
    masked: list[str] = field(default_factory=list)
    replanned: bool = False
    fallback: bool = False
    session_id: str | None = None
    model: str = MODEL
    latency_ms: int = 0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    # Not in the API: the tool calls, an answer that the check stopped and P(injection), for the evaluation and the
    # operator. An attacker must not learn how close a message came to the limit.
    evidence: list[dict] = field(default_factory=list)
    draft: str = ""
    injection: float | None = None


PUBLIC_FIELDS = [name for name in ChatResponse.__dataclass_fields__ if name not in ("evidence", "draft", "injection")]


def _read(response: ChatResponse, state: dict) -> None:
    """Fill the response from the state of this message: every tool call is in its evidence."""
    calls = evidence.read(state)
    names = [(call["tool"].split(".", 1)[1], call["agent"]) for call in calls]
    response.agents_used = list(dict.fromkeys(name for name, agent in names if agent))
    response.tools_used = list(dict.fromkeys(name for name, agent in names if not agent))
    sources = {s.get("url") or s.get("title"): s for call in calls for s in evidence.sources_of(call["result"])}
    response.sources = [source for key, source in sources.items() if key]
    response.ticket = next((call["result"]["ticket"] for call in calls if call["tool"].endswith(".create_ticket")), None)
    response.handoff = response.ticket is not None
    response.tag, response.tag_confidence = state.get("tag", "other"), state.get("tag_confidence")
    response.masked, response.evidence, response.injection = state.get("masked", []), calls, state.get("injection")


_runner: Runner | None = None


def default_runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = Runner(app=app, session_service=DatabaseSessionService(db_engine=store.engine()))
    return _runner


async def _remember(runner: Runner, user_id: str, session_id: str, items: list[dict]) -> None:
    """Add messages to the conversation history in the session state, which keeps the last KEEP_MESSAGES."""
    session = await runner.session_service.get_session(app_name=runner.app_name, user_id=user_id, session_id=session_id)
    history = session.state.get("history", [])
    await runner.session_service.append_event(
        session, Event(author="chat", actions=EventActions(state_delta={"history": (history + items)[-KEEP_MESSAGES:]})))


async def conversation(user_id: str, session_id: str, runner: Runner | None = None) -> list[dict]:
    """The messages of one conversation of this merchant: merchant, assistant and operator."""
    runner = runner or default_runner()
    session = await runner.session_service.get_session(app_name=runner.app_name, user_id=user_id, session_id=session_id)
    if session is None:
        raise SessionNotFound(session_id)
    return session.state.get("history", [])


async def answer_ticket(number: str, answer: str, runner: Runner | None = None) -> dict | None:
    """A person answers a ticket. The answer goes into the merchant's conversation, so the next reply knows it,
    and to the merchant's app at once (notify.py)."""
    runner = runner or default_runner()
    ticket = await handoff.answer_ticket(number, answer)
    if ticket and ticket["session_id"]:
        await _remember(runner, ticket["user_id"], ticket["session_id"],
                        [{"role": "operator", "text": f"({number}) {answer}"}])
    if ticket:
        await notify.send("ticket.answered", ticket)
    return ticket


async def _answer(runner: Runner, user_id: str, session_id: str, message: str) -> str:
    """Run the flow for one message and return the text of the agent that writes to the merchant: the reply agent,
    or the router in an app without one (evals/ablations.py). TagPlugin knows which."""
    writer, answer = runner.plugin_manager.get_plugin("tagger").reply_author, ""
    content = types.Content(role="user", parts=[types.Part(text=message)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content, run_config=RUN_CONFIG):
        if event.error_code == "MODEL_RETURNED_NO_CONTENT":  # an empty answer, which the check sends to a replan
            return ""
        if event.error_code:
            raise RuntimeError(f"{event.error_code}: {event.error_message}")
        if event.author == writer and event.is_final_response() and event.content:
            # TagPlugin added the tag as a part; the JSON has it in `tag`.
            parts = [p for p in event.content.parts or [] if p.text and not p.thought and not tagger.is_tag_part(p)]
            answer = "".join(p.text for p in parts).strip()
    return answer


async def _run(message: str, user_id: str, session_id: str | None, runner: Runner) -> ChatResponse:
    sessions = runner.session_service
    # Mask before the session: the session stores the message.
    message = mask_sensitive(message)
    if session_id and not await sessions.get_session(app_name=runner.app_name, user_id=user_id, session_id=session_id):
        raise SessionNotFound(session_id)
    response = ChatResponse(session_id=session_id)
    try:
        if not session_id:
            response.session_id = (await sessions.create_session(app_name=runner.app_name, user_id=user_id)).id
        for attempt in range(1 + REPLANS):
            response.answer = await _answer(runner, user_id, response.session_id, message)
            session = await sessions.get_session(app_name=runner.app_name, user_id=user_id, session_id=response.session_id)
            _read(response, session.state)
            if (response.injection or 0) > INJECTION_LIMIT:
                raise RuntimeError(f"possible prompt injection (P = {response.injection})")
            if not response.ticket:  # the reply can give a ticket that this conversation already has
                response.ticket = await handoff.open_ticket_in(response.answer, user_id, response.session_id)
                response.handoff = response.ticket is not None
            known = "\n".join([ROUTER_PROMPT, message, *(item["text"] for item in session.state.get("history", []))])
            problem = guardrails.check_reply(response.answer, response.evidence, known)
            if not problem:
                break
            if attempt == REPLANS:
                raise RuntimeError(problem)
            log.info("replan: %s", problem)
            response.replanned = True
            await sessions.append_event(session, Event(author="chat", actions=EventActions(state_delta={"stopped": problem})))
        await _remember(runner, user_id, response.session_id,
                        [{"role": "merchant", "text": message}, {"role": "assistant", "text": response.answer}])
    except Exception as error:  # never an HTTP 500: a person takes over
        log.warning("fallback to handoff: %s", error)
        # No made-up text: the client app tells the merchant that a person takes over this ticket. The person
        # gets the draft that was stopped, if any, to check and reuse.
        response.draft = response.answer
        summary = message[:500] + (f"\n\nDraft, not sent: {response.draft[:1500]}" if response.draft else "")
        response.ticket = await handoff.open_ticket(user_id, response.session_id, f"system: {error}"[:200], summary)
        response.answer, response.handoff, response.fallback = "", True, True
        if response.session_id:
            with suppress(Exception):  # the ticket has the message; the history is a convenience
                await _remember(runner, user_id, response.session_id, [{"role": "merchant", "text": message}])
    return response


async def chat(message: str, user_id: str, session_id: str | None = None, runner: Runner | None = None) -> ChatResponse:
    """Answer one message. Without a session_id, a new conversation starts. Raises SessionNotFound."""
    start = time.monotonic()
    with tracer.start_as_current_span("chat") as span:
        response = await _run(message, user_id, session_id, runner or default_runner())
        response.latency_ms = int((time.monotonic() - start) * 1000)
        labels = {"agents": ",".join(sorted(set(response.agents_used))) or "none", "tag": response.tag,
                  "replanned": response.replanned, "fallback": response.fallback}
        span.set_attributes({**labels, "tools": ",".join(response.tools_used), "handoff": response.handoff,
                             "masked": ",".join(response.masked), "sources": len(response.sources),
                             "tool_calls": len(response.evidence), "tag_confidence": response.tag_confidence or 0.0,
                             "injection": response.injection or 0.0,
                             "request_id": response.request_id})
        REQUESTS.add(1, labels)
        LATENCY.record(response.latency_ms, labels)
        for call in evidence.tool_calls(response.evidence):
            TOOL_CALLS.add(1, call)
    record = {k: v for k, v in asdict(response).items() if k not in ("answer", "sources", "evidence", "draft")}
    log.info(json.dumps({"event": "chat", **record, "sources": len(response.sources)}, ensure_ascii=False))
    return response
