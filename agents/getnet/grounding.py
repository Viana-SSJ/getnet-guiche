"""A free check of faithfulness: every number of an answer must come from the tools.

A number is grounded when the tool calls and results, the assistant's instructions or the dates of yesterday,
today and tomorrow have it, or when it is a total of the amounts of one account tool result or of the
amounts in reais that the instructions have (the conversation so far: a follow-up can add them up).
"""

import json
import re
from datetime import date, timedelta
from itertools import combinations

# A date (2026-11-09, 09/11/2026, 09/11), a time (07:55), a phone number (4002-4000) or a number (1.234,56).
TOKEN = re.compile(
    r"(?<![\w/.,:-])(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}:\d{2}(?::\d{2})?|\d{4,5}[-\u2010\u2011\u2013\u2014 \u00a0]\d{4}"
    r"|\d+(?:[.,]\d+)*)(?=x\b|/\D|[^\w/:-]|$)"  # "48x" and "14,90/mês" are numbers, "S920" is a name
)
SUM_TOOLS = ("get_receivables", "get_recent_transactions")  # their amounts can add up to a total
MONEY = re.compile(r"R\$\s*(\d+(?:[.,]\d+)*)")  # "R$ 116,77"
FILE_DATE = re.compile(r"(?<!\d)(?:19|20)\d\d(\d\d)(\d\d)(?!\d)")  # 20260813 in "20260813_contrato.pdf"
MAX_SUM_TERMS = 14


def _number(text: str) -> float | None:
    """With both separators (1.234,56 or 1,234.56) the last one is the decimal one. A single one is decimal
    (45,12 or 5.514), on both sides of the check, so the same text gives the same value."""
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        text = text.replace("." if decimal == "," else ",", "").replace(decimal, ".")
    elif "," in text:
        text = text.replace(",", ".") if text.count(",") == 1 else text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return round(float(text), 4)
    except ValueError:
        return None


def normalise(token: str) -> str | None:
    """One form for each value: a date becomes "11-09" (month and day), a phone number its digits."""
    if m := re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", token):
        return f"{m[1]}-{m[2]}"
    if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/\d{2,4})?", token):
        return f"{int(m[2]):02d}-{int(m[1]):02d}"
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", token):
        hours, minutes = token.split(":")[:2]
        return f"{int(hours):02d}:{minutes}"
    if re.fullmatch(r"\d{4,5}[-\u2010\u2011\u2013\u2014 \u00a0]\d{4}", token):
        return re.sub(r"\D", "", token)
    value = _number(token)
    return None if value is None else f"{value:g}"


def values(text: str) -> list[str]:
    return [v for v in (normalise(t) for t in TOKEN.findall(text)) if v]


def _totals(amounts: list[float]) -> set[str]:
    amounts = amounts[:MAX_SUM_TERMS]
    return {f"{round(sum(c), 4):g}" for size in range(2, len(amounts) + 1) for c in combinations(amounts, size)}


def ungrounded(answer: str, evidence: list[dict], instructions: str, today: date | None = None) -> list[str]:
    """The numbers of the answer that no tool call or result supports. Small counts (0 to 10) and years are free.

    `evidence`: {"tool": "<agent>.<tool>", "args": ..., "result": ...} for each tool call.
    """
    today = today or date.today()
    allowed = set(values(instructions)) | _totals([_number(m) for m in MONEY.findall(instructions)])
    for day in (today - timedelta(days=1), today, today + timedelta(days=1)):
        allowed |= {day.strftime("%m-%d"), f"{day.year}"}
    for item in evidence:
        text = json.dumps(item, ensure_ascii=False)
        numbers = values(text)
        # Also the digits inside names ("202403_Termo.pdf"), and a date in a file name ("20260813_contrato.pdf").
        allowed |= set(numbers) | {f"{int(d):g}" for d in re.findall(r"\d+", text)}
        allowed |= {f"{month}-{day}" for month, day in FILE_DATE.findall(text)}
        if not item["tool"].endswith(SUM_TOOLS):
            continue
        allowed |= _totals([float(n) for n in numbers if re.fullmatch(r"-?\d+(\.\d+)?", n)])
    missing = []
    for token in TOKEN.findall(answer):
        value = normalise(token)
        if value is None or value in allowed:
            continue
        if re.fullmatch(r"\d+", value) and (int(value) <= 10 or 1990 <= int(value) <= 2100):
            continue
        missing.append(token)
    return missing
