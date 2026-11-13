"""Compare runs of the dev set on the same cases: the models (with docs/cost-quality.svg) and the ablations.

    uv run python -m evals.compare models
    uv run python -m evals.compare evals/results/<reference>.json evals/results/<other>.json ...

evals/results/models.json lists each model run with its measured cost (the change of the OpenRouter key's
usage, one run at a time, no fallback model). The second form compares any runs of the same cases with the
first one; a run's measured cost, if any, is in its summary (`cost_usd`).
Every share has a 95 % Wilson interval; a run against the reference has the cases it won and lost, and the
exact McNemar p (a two-sided sign test on those discordant cases).
"""

import json
import sys
from math import ceil, comb, floor, sqrt
from pathlib import Path

RESULTS = Path("evals/results")
OUT = Path("docs/cost-quality.svg")
W, H, LEFT, RIGHT, TOP, BOTTOM = 640, 360, 70, 30, 40, 60


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The 95 % Wilson interval of a share k/n: right also near 0 and 1, where the normal one is not."""
    if not n:
        return 0.0, 1.0
    p = k / n
    centre, half = p + z * z / (2 * n), z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n)


def mcnemar(won: int, lost: int) -> float:
    """The exact two-sided p of the discordant cases, if each one were a coin toss (a sign test)."""
    total = won + lost
    tail = sum(comb(total, count) for count in range(min(won, lost) + 1))
    return min(1.0, 2 * tail / 2**total) if total else 1.0


def load(path: Path, label: str, cost: float | None = None) -> dict:
    data = json.loads(path.read_text())
    rows, summary = data["rows"], data["summary"]
    cost = summary.get("cost_usd", cost)
    calls = [len(r["reply"]["evidence"]) for r in rows]
    return {"label": label, "file": path, "n": len(rows), "passed": [not r["failed"] for r in rows],
            "tools": sum(1 for r in rows if not any(f.startswith("tools") for f in r["failed"])),
            "fallbacks": summary["fallbacks"], "p50": summary["latency_ms_p50"] / 1000, "p95": summary["latency_ms_p95"] / 1000,
            "calls": sum(calls) / len(rows), "cost": cost / len(rows) if cost is not None else None}


def table(runs: list[dict], reference: dict) -> str:
    lines = [f"| | Passed (95 % CI) | Tools | Fallbacks | p50 / p95 | Tool calls per message | US$ per message"
             f" | Against {reference['label']}: won / lost, exact p |", "|---|---|---|---|---|---|---|---|"]
    for run in runs:
        k, n = sum(run["passed"]), run["n"]
        low, high = wilson(k, n)
        if run is reference:
            versus = ""
        else:
            won = sum(1 for a, b in zip(reference["passed"], run["passed"]) if b and not a)
            lost = sum(1 for a, b in zip(reference["passed"], run["passed"]) if a and not b)
            versus = f"{won} / {lost}, p = {mcnemar(won, lost):.2f}"
        cost = f"{run['cost']:.5f}" if run["cost"] is not None else "—"
        lines.append(f"| {run['label']} | {k}/{n} ({low:.0%}–{high:.0%}) | {run['tools']}/{n} | {run['fallbacks']} "
                     f"| {run['p50']:.1f} s / {run['p95']:.1f} s | {run['calls']:.1f} | {cost} | {versus} |")
    return "\n".join(lines)


def frontier(runs: list[dict]) -> list[dict]:
    """The models that no cheaper model beats: from the cheapest, keep each one that passes more."""
    best, keep = -1, []
    for run in sorted(runs, key=lambda r: r["cost"]):
        if sum(run["passed"]) > best:
            best, keep = sum(run["passed"]), [*keep, run]
    return keep


def svg(runs: list[dict]) -> str:
    # A scatter needs no zero baseline: the axes span the data, in round steps.
    costs, shares = [r["cost"] for r in runs], [sum(r["passed"]) / r["n"] for r in runs]
    x0, x1 = floor(min(costs) * 0.9 / 1e-4) * 1e-4, ceil(max(costs) * 1.1 / 1e-4) * 1e-4
    y0, y1 = floor((min(shares) - 0.05) * 20) / 20, 1.0
    x = lambda cost: LEFT + (cost - x0) / (x1 - x0) * (W - LEFT - RIGHT)  # noqa: E731
    y = lambda share: H - BOTTOM - (share - y0) / (y1 - y0) * (H - TOP - BOTTOM)  # noqa: E731
    grid = "".join(f'<line class="grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{y(s):.1f}" y2="{y(s):.1f}"/>'
                   f'<text class="axis" x="{LEFT - 8}" y="{y(s) + 4:.1f}" text-anchor="end">{s:.0%}</text>'
                   for s in (y0 + 0.05 * i for i in range(round((y1 - y0) / 0.05) + 1)))
    grid += "".join(f'<text class="axis" x="{x(c):.1f}" y="{H - BOTTOM + 18}" text-anchor="middle">${c:.4f}</text>'
                    for c in (x0 + 1e-4 * i for i in range(round((x1 - x0) / 1e-4) + 1)))
    line = " ".join(f"{x(r['cost']):.1f},{y(sum(r['passed']) / r['n']):.1f}" for r in frontier(runs))
    dots, top = "", max(runs, key=lambda r: sum(r["passed"]))
    for r in runs:
        cx, cy = x(r["cost"]), y(sum(r["passed"]) / r["n"])
        # Above the best point and below the others, away from the dashed line; anchored to the side with room.
        anchor = "start" if cx < (LEFT + W - RIGHT) / 2 else "end"
        dots += (f'<circle class="dot" cx="{cx:.1f}" cy="{cy:.1f}" r="6"/>'
                 f'<text class="label" x="{cx:.1f}" y="{cy - 14 if r is top else cy + 24:.1f}" text-anchor="{anchor}">'
                 f'{r["label"]} · {sum(r["passed"])}/{r["n"]} · p95 {r["p95"]:.0f} s</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
  aria-label="Passed dev cases against the cost per message, one point per model">
<style>
  .bg {{ fill: #fcfcfb }} .grid {{ stroke: #e4e3df; stroke-width: 1 }} .axis {{ fill: #52514e; font: 12px sans-serif }}
  .title {{ fill: #0b0b0b; font: 600 14px sans-serif }} .label {{ fill: #0b0b0b; font: 12px sans-serif }}
  .dot {{ fill: #2a78d6; stroke: #fcfcfb; stroke-width: 2 }} .front {{ fill: none; stroke: #52514e; stroke-width: 2; stroke-dasharray: 5 4 }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ fill: #1a1a19 }} .grid {{ stroke: #3a3a37 }} .axis {{ fill: #c3c2b7 }} .title, .label {{ fill: #f0efec }}
    .dot {{ fill: #3987e5; stroke: #1a1a19 }} .front {{ stroke: #c3c2b7 }}
  }}
</style>
<rect class="bg" width="{W}" height="{H}"/>
<text class="title" x="{LEFT}" y="22">Dev set passed vs cost per message (dashed: the Pareto front)</text>
{grid}<polyline class="front" points="{line}"/>{dots}
<text class="axis" x="{(LEFT + W - RIGHT) / 2}" y="{H - 16}" text-anchor="middle">US$ per message (measured)</text>
</svg>
'''


if __name__ == "__main__":
    if sys.argv[1:] == ["models"]:
        runs = [load(Path(run["results"]), run["model"].split("/")[-1], run["cost_usd"])
                for run in json.loads((RESULTS / "models.json").read_text())]
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(svg(runs))
        print(table(sorted(runs, key=lambda r: r["cost"]), max(runs, key=lambda r: sum(r["passed"]))))
    else:
        runs = [load(Path(f), Path(f).stem.removeprefix("ablation-").rsplit("-", 2)[0]) for f in sys.argv[1:]]
        print(table(runs, runs[0]))
