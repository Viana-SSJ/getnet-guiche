"""Measure search_kb: hit@1, hit@3, hit@6 and the mean reciprocal rank of the expected page.

    uv run python -m evals.retrieval evals/retrieval_dev.jsonl [more sets]
"""

import json
import sys
from pathlib import Path

from agents.getnet.tools.kb_search import TOP_K, load_index


def rank(results: list[dict], case: dict) -> int | None:
    """The rank of the first result on an expected page (and, if named, with the expected passage)."""
    for number, result in enumerate(results, 1):
        url = result["url"].lower()
        if any(e.lower() in url for e in case["expect"]) and case.get("expect_text", "") in result["text"]:
            return number
    return None


if __name__ == "__main__":
    index = load_index()
    for path in sys.argv[1:]:
        cases = [json.loads(line) for line in Path(path).read_text().splitlines()]
        ranks = [rank(index.search(case["query"]), case) for case in cases]
        found = [r for r in ranks if r]
        hits = "  ".join(f"hit@{k} {sum(r <= k for r in found)}/{len(cases)}" for k in (1, 3, TOP_K))
        print(f"{Path(path).stem:22} {hits}  MRR {sum(1 / r for r in found) / len(cases):.2f}")
