"""Run an evaluation set against the real model and save the results.

A second final run needs --again. With --min-pass 0.9, exit with an error below 90 % passed (for CI).
"""

import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

RESULTS = Path("evals/results")
# An expected agent counts as called when one of its tools was called, so that a design with no agent tools
# (a single agent) is scored the same way.
OWNER = {"search_kb": "knowledge", "web_search": "knowledge", "get_weather": "knowledge", "get_exchange_rate": "knowledge",
         "get_receivables": "support", "get_terminal_status": "support", "get_recent_transactions": "support"}
MAX_FALLBACKS_IN_A_ROW = 3  # usually a rate limit: stop, do not spend the quota on errors


def check(case: dict, reply: dict) -> list[str]:
    """Return the failed checks. `expect`: one of these tools must be called; an empty list: no tool.

    `before`: earlier messages of the same conversation; only the last message is checked.
    `expect_all`: every one of these agents must be used. `must_contain`: for each list, one of its forms
    must be in the answer (a fact that only a tool knows, such as an amount).
    """
    failed = []
    used = reply["agents_used"] + reply["tools_used"] + [OWNER[t] for t in reply["tools_used"] if t in OWNER]
    if "expect" in case:
        if case["expect"] and not set(case["expect"]) & set(used):
            failed.append(f"tools {used} include none of {case['expect']}")
        if not case["expect"] and used:
            failed.append(f"tools {used} used, but none expected")
    for agent in case.get("expect_all", []):  # every source that the message needs
        if agent not in used:
            failed.append(f"{agent} not used")
    for options in case.get("must_contain", []):  # a fact that only a tool knows, in any of these forms
        if not any(option in reply["answer"] for option in options):
            failed.append(f"answer has none of {options}")
    if set(case.get("masked", [])) - set(reply["masked"]):
        failed.append(f"masked {reply['masked']}, expected {case['masked']}")
    if "tag" in case:
        tags = case["tag"] if isinstance(case["tag"], list) else [case["tag"]]
        if reply["tag"] not in tags:
            failed.append(f"tag {reply['tag']} not in {tags}")
    if case.get("injection"):  # a person must take over
        if not reply["fallback"]:
            failed.append("injection not stopped")
    else:
        if not reply["answer"].strip():
            failed.append("empty answer")
        if reply["fallback"]:
            failed.append("fallback to handoff (system error)")
    if "search_kb" in reply["tools_used"] and not any("getnet.com.br" in (s.get("url") or "") for s in reply["sources"]):
        failed.append("knowledge base answer without a site.getnet.com.br source")
    for text in case.get("must_not_contain", []):
        if text in reply["answer"]:
            failed.append(f"answer contains forbidden text {text!r}")
    return failed


async def main(path: Path, again: bool, min_pass: float | None = None, runner=None, name: str | None = None) -> dict:
    """Run one set and save its results. `runner` and `name`: for an ablation (evals/ablations.py)."""
    load_dotenv()
    from agents.getnet.chat import chat
    from agents.getnet.evidence import tool_calls
    from agents.getnet.tools.kb_search import load_index

    RESULTS.mkdir(parents=True, exist_ok=True)
    if path.stem == "final" and any(RESULTS.glob("final-*.json")) and not again:
        sys.exit("The final set has already run. Use --again only if you also report it in the README.")
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    load_index()
    rows = []
    for number, case in enumerate(cases, 1):
        session_id, earlier_evidence = None, []
        for earlier in case.get("before", []):  # earlier messages of the same conversation
            earlier_reply = await chat(earlier, case["user_id"], session_id, runner)
            session_id, earlier_evidence = earlier_reply.session_id, [*earlier_evidence, *earlier_reply.evidence]
        reply = asdict(await chat(case["message"], case["user_id"], session_id, runner))
        reply["evidence"] = [*earlier_evidence, *reply["evidence"]]
        failed = check(case, reply)
        rows.append({"case": case, "reply": reply, "failed": failed})
        mark = "PASS" if not failed else "FAIL"
        used = ",".join(reply["agents_used"] + reply["tools_used"]) or "-"
        print(f"[{number:2}/{len(cases)}] {mark} {used[:28]:28} {reply['tag']:11} {reply['latency_ms']:6} ms  {case['message'][:45]}"
              + (f"\n          {failed}" if failed else ""), flush=True)
        if len(rows) >= MAX_FALLBACKS_IN_A_ROW and all(r["reply"]["fallback"] for r in rows[-MAX_FALLBACKS_IN_A_ROW:]):
            sys.exit(f"Stopped: {MAX_FALLBACKS_IN_A_ROW} system errors in a row. Check the log for rate limits (HTTP 429).")

    tools_ok = sum(1 for r in rows if not any(f.startswith("tools") for f in r["failed"]))
    tags_ok = sum(1 for r in rows if not any(f.startswith("tag") for f in r["failed"]))
    latencies = sorted(r["reply"]["latency_ms"] for r in rows)
    summary = {
        "set": str(path),
        "cases": len(rows),
        "passed": sum(1 for r in rows if not r["failed"]),
        "tool_accuracy": round(tools_ok / len(rows), 3),
        "tag_accuracy": round(tags_ok / len(rows), 3),
        "empty_answers": sum(1 for r in rows if not r["reply"]["answer"].strip()),
        "fallbacks": sum(1 for r in rows if r["reply"]["fallback"]),
        # The process, not only the result: how the agents used their tools.
        "tool_calls_per_message": round(sum(len(r["reply"]["evidence"]) for r in rows) / len(rows), 2),
        "repeated_or_blocked_calls": sum(1 for r in rows for c in tool_calls(r["reply"]["evidence"]) if c["kind"] != "run"),
        # A question that the knowledge base cannot answer passes only when the agent invents nothing.
        "absent_passed": f'{sum(1 for r in rows if r["case"].get("absent") and not r["failed"])}/{sum(1 for r in rows if r["case"].get("absent"))}',
        "latency_ms_p50": int(statistics.median(latencies)),
        "latency_ms_p95": latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))],
        "model": rows[0]["reply"]["model"],
    }
    out = RESULTS / f"{name or path.stem}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, indent=2), f"\nSaved {out}")
    if min_pass is not None and summary["passed"] < min_pass * summary["cases"]:
        sys.exit(f"Passed {summary['passed']}/{summary['cases']}, below {min_pass:.0%}.")
    return summary


if __name__ == "__main__":
    args = sys.argv[1:]
    min_pass = float(args[args.index("--min-pass") + 1]) if "--min-pass" in args else None
    asyncio.run(main(Path(args[0]), "--again" in args, min_pass))
