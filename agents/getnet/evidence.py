"""The evidence of a message: every tool call of every agent, with its arguments and result.

The API fields, the answer check, the number check, the metrics and the judge all read it. The events of
an agent tool stay inside it, but its state reaches the session, so the callbacks write to the state.
Agent tools can run at once, and each one merges its state into the session: so no callback reads,
changes and writes back a shared value; each one writes a key of its own, under the turn that `guard`
starts.
"""

import json
import time
import uuid

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.tools import BaseTool, ToolContext
from google.adk.tools.agent_tool import AgentTool

MAX_TOOL_CALLS = 6  # of each agent, for one message


def _calls_key(context) -> str:
    return f"calls.{context.state.get('turn')}.{context.agent_name}"


def limit_calls(tool: BaseTool, args: dict, tool_context: ToolContext) -> dict | None:
    """Stop a loop: after MAX_TOOL_CALLS calls of one agent, a tool returns an error instead of running."""
    key = _calls_key(tool_context)
    tool_context.state[key] = tool_context.state.get(key, 0) + 1
    if tool_context.state[key] > MAX_TOOL_CALLS:
        return {"error": f"Limit of {MAX_TOOL_CALLS} tool calls for one message. Answer with what you have."}
    return None


def no_tools_after_limit(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """A model can ignore the limit error and call again until max_llm_calls: after the limit, it gets no tools,
    so it must write its answer."""
    if callback_context.state.get(_calls_key(callback_context), 0) >= MAX_TOOL_CALLS and llm_request.config:
        llm_request.config.tools = None



def record_tool(tool: BaseTool, args: dict, tool_context: ToolContext, tool_response) -> None:
    """Write the call and its result to the state, under a key of its own."""
    call = {"tool": f"{tool_context.agent_name}.{tool.name}", "agent": isinstance(tool, AgentTool),
            "args": args, "result": tool_response}
    tool_context.state[f"evidence.{tool_context.state.get('turn')}.{time.time_ns()}.{uuid.uuid4().hex[:6]}"] = call


def read(state: dict) -> list[dict]:
    """The tool calls of the current message (the session state as a dict), in the order they ended."""
    prefix = f"evidence.{state.get('turn')}."
    return [state[key] for key in sorted(k for k in state if k.startswith(prefix))]


def sources_of(result) -> list[dict]:
    """The documents and sites of a tool result: search results, or a `source`."""
    if not isinstance(result, dict):
        return []
    if "results" in result:
        return [{"title": r.get("title"), "url": r.get("url")} for r in result["results"]]
    if "source" in result:
        return [{"title": result["source"], "url": result["source"] if result["source"].startswith("http") else None}]
    return []


def tool_calls(evidence: list[dict]) -> list[dict]:
    """Each tool call: the calling agent, and its kind. `repeat`: the same tool with the same arguments as an
    earlier call of the message, which a good plan does not need. `blocked`: stopped by the limit."""
    seen, calls = set(), []
    for call in evidence:
        key = (call["tool"], json.dumps(call["args"], sort_keys=True, ensure_ascii=False))
        blocked = isinstance(call["result"], dict) and str(call["result"].get("error", "")).startswith("Limit of")
        calls.append({"agent": call["tool"].split(".", 1)[0], "kind": "blocked" if blocked else "repeat" if key in seen else "run"})
        seen.add(key)
    return calls


# The callbacks of every agent that calls tools.
CALLBACKS = {"before_model_callback": no_tools_after_limit, "before_tool_callback": limit_calls,
             "after_tool_callback": record_tool}
