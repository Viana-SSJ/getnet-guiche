"""The prompt injection detector: P(injection) of the decision model, on attacks and on normal messages.

    uv run python -m evals.injection score    # one decision call for each message (about 1,100, US$ 0.006)
    uv run python -m evals.injection          # the threshold and the results, from the last scores

The sets. Attacks: 300 in Portuguese (Weni/prompt-injections-1.0.0, translated from HackAPrompt), 60 in
English and German (the test split of deepset/prompt-injections), and the attacks of our dev set.
Normal messages: the 309 questions of the Getnet FAQ, the other messages of our dev and final sets, and the
56 normal texts of the deepset test split. The external sets are read at a fixed revision.

The threshold is split conformal on normal messages: half of the FAQ questions (a fixed shuffle) calibrates
it, so that a new normal message from the same source is flagged with a chance of at most ALPHA. Every other
normal set tests it. Exchangeability is the assumption: merchant messages are not FAQ questions, so the test
on our own dev and final messages matters more than the guarantee.
"""

import asyncio
import io
import json
import random
import sys
import time
from pathlib import Path

import httpx
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

from agents.getnet.tagger import classify  # noqa: E402
from evals.compare import wilson  # noqa: E402
from evals.judge import conformal_threshold  # noqa: E402

RESULTS = Path("evals/results")
ALPHA = 0.01
HF = "https://huggingface.co/datasets"
WENI = f"{HF}/Weni/prompt-injections-1.0.0/resolve/9707fa47b35b92f2cad2112632710e1b4bef0416/data/train-00000-of-00001.parquet"
DEEPSET = f"{HF}/deepset/prompt-injections/resolve/4f61ecb038e9c3fb77e21034b22511b523772cdd/data/test-00000-of-00001-701d16158af87368.parquet"


def _parquet(url: str) -> list[dict]:
    response = httpx.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    return pq.read_table(io.BytesIO(response.content)).to_pylist()


def _ours(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def messages() -> list[dict]:
    """Every message with its set; `attack` is True for an injection."""
    rows = [{"set": "attacks-pt", "id": i, "text": r["text"], "attack": True} for i, r in enumerate(_parquet(WENI))]
    for i, r in enumerate(_parquet(DEEPSET)):
        rows.append({"set": "attacks-en-de" if r["label"] else "normal-en-de", "id": i, "text": r["text"], "attack": bool(r["label"])})
    faq = [r["query"] for r in _ours("evals/retrieval_faq_pt.jsonl")]
    order = list(range(len(faq)))
    random.Random(0).shuffle(order)
    rows += [{"set": "faq-calibration" if n < len(faq) // 2 else "faq-test", "id": i, "text": faq[i], "attack": False}
             for n, i in enumerate(order)]
    for name in ("dev", "final"):
        for i, case in enumerate(_ours(f"evals/{name}.jsonl")):
            attack = case.get("injection", False)
            rows.append({"set": "attacks-ours" if attack else f"normal-{name}", "id": i, "text": case["message"], "attack": attack})
    return rows


async def score() -> Path:
    rows, limit = messages(), asyncio.Semaphore(8)

    async def one(row: dict) -> None:
        async with limit:
            row["p"] = (await classify(row["text"]))[2]

    await asyncio.gather(*(one(row) for row in rows))
    for row in rows:  # the external texts are not ours to publish again: keep their index only
        if not row["set"].startswith(("faq", "normal-dev", "normal-final", "attacks-ours")):
            del row["text"]
    out = RESULTS / f"injection-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=1))
    print(f"Saved {out}")
    return out


def threshold(rows: list[dict]) -> float:
    return conformal_threshold([r["p"] for r in rows if r["set"] == "faq-calibration"], ALPHA)


def report(path: Path) -> dict:
    rows = json.loads(path.read_text())["rows"]
    limit = threshold(rows)
    sets = {}
    for name in dict.fromkeys(r["set"] for r in rows if r["set"] != "faq-calibration"):
        group = [r for r in rows if r["set"] == name]
        flagged = sum(r["p"] > limit for r in group)
        low, high = wilson(flagged, len(group))
        sets[name] = {"flagged": f"{flagged}/{len(group)}", "ci95": f"{low:.0%}–{high:.0%}"}
    summary = {"results": path.name, "alpha": ALPHA, "threshold": limit, "sets": sets}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    path = asyncio.run(score()) if sys.argv[1:] == ["score"] else sorted(RESULTS.glob("injection-*.json"))[-1]
    report(path)
