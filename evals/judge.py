"""Check that each answer says only what the tool results and the instructions support (faithfulness).

    uv run python -m evals.judge evals/results/dev-<time>.json
    uv run python -m evals.judge evals/results/final-<time>.json --corrupt
    uv run python -m evals.judge calibrate

Two checks. The gate: every number must come from the tools (agents/getnet/grounding.py, free; the
API runs it on every answer too). The triage: a decision model (no web search) gives the probability
that the answer is faithful, and a person reads the answers below a threshold. The labels in
evals/labels.jsonl say which answers of one run are faithful.

The threshold comes from split conformal prediction: from the scores of the unfaithful answers of the
calibration runs, it is the smallest one that has at least 1 - ALPHA of them at or below it. If the
unfaithful answers of a new run are like those of the calibration runs (exchangeable), the triage flags
each one with a chance of at least 1 - ALPHA. The guarantee is on average over calibration sets, not
for each run, and only for answers like the calibration answers: a new model or prompt needs new labels.
`calibrate` checks it on the labelled runs that are not in the calibration set.
With --corrupt, each labelled faithful answer also gets a copy with one number changed, which must fail.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from math import ceil, sqrt
from pathlib import Path

from dotenv import load_dotenv

from agents.getnet.decisions import MODEL as DECISION_MODEL
from agents.getnet.decisions import decide
from agents.getnet.grounding import ungrounded
from agents.getnet.router import PROMPT as ROUTER_PROMPT

LABELS = Path("evals/labels.jsonl")
MAX_RESULT_CHARS = 6_000  # for each tool result, so that a long search does not hide a later tool
RESULTS = Path("evals/results")
# The labelled runs of 2026-11-09 calibrate the triage; the labelled runs of 2026-11-10 (later code) test it.
CALIBRATION = ["dev-20261109-162610", "ablation-baseline-20261109-221337", "ablation-baseline-20261109-232037",
               "final-20261109-162928", "final-20261109-185730"]
ALPHA = 0.2  # the triage must flag at least 80 % of the unfaithful answers

QUESTION = """
Does the answer say only what the tool results and the instructions support?
Yes, when every number, amount, fee, date, deadline, phone number, opening hours, step, rule, policy,
product feature and name in the answer is in the tool results or the instructions, and is given to
the right product, machine model, channel and case.
These do not count against the answer: wording, summaries, translations, correct sums, greetings,
offers to help, questions to the merchant, refusals of off-topic requests, "do not send card data in
the chat", advice that adds no new fact, and a ticket number that create_ticket returned.
No, when the answer has one fact that is not there, or one fact given to the wrong case.
"""


def judge(row: dict, today: date) -> dict:
    reply = row["reply"]
    # The same check as the API: the message and the earlier messages of the conversation are sources too.
    known = "\n".join([ROUTER_PROMPT, row["case"]["message"], *row["case"].get("before", [])])
    numbers = ungrounded(reply["answer"], reply["evidence"], known, today)
    evidence = "\n".join(json.dumps(item, ensure_ascii=False)[:MAX_RESULT_CHARS] for item in reply["evidence"])
    state = (f"Today: {today:%Y-%m-%d (%A)}\n\n<instructions>\n{ROUTER_PROMPT.strip()}\n</instructions>\n\n"
             f"<message>\n{row['case']['message']}\n</message>\n\n<tool_results>\n{evidence or '[]'}\n</tool_results>\n\n"
             f"<answer>\n{reply['answer']}\n</answer>")
    probability = decide(state, {"faithful": {"type": "noul", "instructions": QUESTION.strip()}})["faithful"]["noul"]
    return {"faithful": not numbers, "ungrounded_numbers": numbers, "p_faithful": round(probability, 4)}


def corrupt(answer: str, evidence: str) -> str | None:
    """Change the last digit of a number that the tools returned (an amount first; no year, date or time)."""
    evidence += evidence.replace(".", ",")  # "45.12" in JSON is "45,12" in a Portuguese answer
    numbers = [m for m in re.finditer(r"(?<![\w/:-])\d+(?:[.,]\d+)*(?![\w/:-])", answer)
               if len(re.sub(r"\D", "", m.group())) >= 2 and not re.fullmatch(r"(19|20)\d\d", m.group())
               and m.group() in evidence]
    for match in sorted(numbers, key=lambda m: not re.search(r"[.,]", m.group())):
        number = match.group()
        for step in range(1, 10):
            changed = number[:-1] + str((int(number[-1]) + step) % 10)
            if changed not in evidence:
                return answer[:match.start()] + changed + answer[match.end():]
    return None


def agreement(rows: list[dict], check) -> dict:
    """A check against the labels: the unfaithful answers it caught, and its false alarms on faithful ones."""
    labelled = [(r["label"], not check(r)) for r in rows if r["label"] is not None]
    caught = [flagged for label, flagged in labelled if not label]
    alarms = [flagged for label, flagged in labelled if label]
    return {"caught_unfaithful": f"{sum(caught)}/{len(caught)}", "false_alarms": f"{sum(alarms)}/{len(alarms)}"}


def auc(rows: list[dict]) -> dict | None:
    """The chance that a faithful answer gets a higher P(faithful) than an unfaithful one (1.0 is perfect), with
    its 95 % interval (Hanley and McNeil, 1982): with few unfaithful answers, the interval is wide."""
    good = [r["judge"]["p_faithful"] for r in rows if r["label"] is True]
    bad = [r["judge"]["p_faithful"] for r in rows if r["label"] is False]
    if not good or not bad:
        return None
    a = sum((g > b) + 0.5 * (g == b) for g in good for b in bad) / (len(good) * len(bad))
    q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
    se = sqrt((a * (1 - a) + (len(bad) - 1) * (q1 - a * a) + (len(good) - 1) * (q2 - a * a)) / (len(good) * len(bad)))
    return {"auc": round(a, 3), "ci95": [round(max(0, a - 1.96 * se), 2), round(min(1, a + 1.96 * se), 2)],
            "faithful": len(good), "unfaithful": len(bad)}


def conformal_threshold(scores: list[float], alpha: float = ALPHA) -> float:
    """The split conformal threshold: the ceil((n + 1)(1 - alpha))-th smallest of n calibration scores. A new score
    of the same kind is at most this value with a chance of at least 1 - alpha."""
    rank = ceil((len(scores) + 1) * (1 - alpha))
    if rank > len(scores):
        raise ValueError(f"{len(scores)} scores cannot give a guarantee of {1 - alpha:.0%}")
    return sorted(scores)[rank - 1]


def labelled(stem: str) -> list[dict]:
    """The judged answers of a run that have a label."""
    return [r for r in json.loads((RESULTS / f"judge-{stem}.json").read_text())["rows"] if r["label"] is not None]


def threshold() -> float:
    return conformal_threshold([r["judge"]["p_faithful"] for stem in CALIBRATION for r in labelled(stem) if not r["label"]])


def calibrate() -> None:
    """The threshold from the calibration runs, and how it does on the other labelled runs."""
    limit = threshold()
    tests = sorted({item["results"] for item in map(json.loads, LABELS.read_text().splitlines())} - set(CALIBRATION))
    rows = [r for stem in tests for r in labelled(stem)]
    flagged = [r for r in rows if r["judge"]["p_faithful"] <= limit]
    print(json.dumps({"alpha": ALPHA, "threshold": limit, "test_runs": tests, "test": {
        **agreement(rows, lambda r: r["judge"]["p_faithful"] > limit), **(auc(rows) or {}),
        "read": f"{len(flagged)}/{len(rows)}"}}, indent=2))


def main(path: Path, with_corrupt: bool) -> None:
    load_dotenv()
    stamp = re.search(r"(\d{4})(\d{2})(\d{2})-\d{6}", path.name)  # the day of the run: "yesterday" depends on it
    today = date(*map(int, stamp.groups())) if stamp else date.today()
    # A label is about one answer, so it counts only for the run that was labelled.
    labels = {item["message"]: item["faithful"] for item in map(json.loads, LABELS.read_text().splitlines())
              if item["results"] == path.stem}
    rows = [{**r, "label": labels.get(r["case"]["message"])}
            for r in json.loads(path.read_text())["rows"] if r["reply"]["answer"].strip()]  # empty: a fallback
    if with_corrupt:
        for row in [r for r in rows if r["label"]]:
            if changed := corrupt(row["reply"]["answer"], json.dumps(row["reply"]["evidence"], ensure_ascii=False)):
                rows.append({**row, "label": False, "case": {**row["case"], "message": row["case"]["message"] + " [one number changed]"},
                             "reply": {**row["reply"], "answer": changed}})
    limit = threshold()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for row, verdict in zip(rows, pool.map(lambda r: judge(r, today), rows)):
            row["judge"] = verdict
    for number, row in enumerate(rows, 1):
        verdict = row["judge"]
        print(f"[{number:2}/{len(rows)}] {'ok ' if verdict['faithful'] else 'BAD'} p={verdict['p_faithful']:.3f} label={row['label']!s:5}"
              f" {row['case']['message'][:50]}" + (f"  numbers: {verdict['ungrounded_numbers']}" if verdict["ungrounded_numbers"] else ""))
    summary = {"results": str(path), "judge_model": DECISION_MODEL, "judged": len(rows),
               "faithful": sum(r["judge"]["faithful"] for r in rows),
               "number_check": agreement(rows, lambda r: r["judge"]["faithful"]),
               "decision_model": {**(auc(rows) or {}), "threshold": limit,
                                  "triage": agreement(rows, lambda r: r["judge"]["p_faithful"] > limit)}}
    out = path.with_name(f"judge-{path.stem}{'-corrupt' if with_corrupt else ''}.json")
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, indent=2), f"\nSaved {out}")


if __name__ == "__main__":
    if sys.argv[1] == "calibrate":
        calibrate()
    else:
        main(Path(sys.argv[1]), "--corrupt" in sys.argv)
