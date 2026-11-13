"""Account tools over mock data. They read the merchant from the session, never from the model."""

import json
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "customers.json"
# Business days from the sale to the payment.
SETTLEMENT_DAYS = {"debit": 1, "credit": 2, "pix": 0}


@cache
def customers() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _customer(tool_context: ToolContext) -> dict | None:
    return customers().get(tool_context.user_id)


def add_business_days(day: date, count: int) -> date:
    while count > 0:
        day += timedelta(days=1)
        if day.weekday() < 5:
            count -= 1
    return day


def _sale_date(item: dict, today: date) -> date:
    return today + timedelta(days=item["day_offset"])


def get_receivables(sale_date: str, tool_context: ToolContext) -> dict:
    """Get when the approved sales of one day are paid into the merchant's account.

    Args:
        sale_date: The day of the sales, in the format YYYY-MM-DD.

    Returns:
        Each approved sale with its gross amount, fee, net amount and payment date.
    """
    customer = _customer(tool_context)
    if customer is None:
        return {"error": "Merchant not found."}
    try:
        day = date.fromisoformat(sale_date)
    except ValueError:
        return {"error": "Use the format YYYY-MM-DD for sale_date."}
    today = date.today()
    rows = []
    for item in customer["transactions"]:
        if item["status"] != "approved" or _sale_date(item, today) != day:
            continue
        fee = round(item["amount"] * customer["rates"][item["method"]] / 100, 2)
        rows.append({
            "transaction": item["id"],
            "method": item["method"],
            "installments": item.get("installments", 1),
            "gross": item["amount"],
            "fee": fee,
            "net": round(item["amount"] - fee, 2),
            "payment_date": add_business_days(day, SETTLEMENT_DAYS[item["method"]]).isoformat(),
        })
    return {
        "sale_date": day.isoformat(),
        "account": customer["account"],
        "receivables": rows,
        "note": "Approved sales only. Credit sales in instalments are paid in full in 2 business days "
                "(no sales advance cost).",
    }


def get_terminal_status(tool_context: ToolContext) -> dict:
    """Get the status of the merchant's card machines: online or offline, connection, signal and last error.

    Returns:
        The list of terminals of the merchant.
    """
    customer = _customer(tool_context)
    if customer is None:
        return {"error": "Merchant not found."}
    return {"terminals": customer["terminals"]}


def get_recent_transactions(days: int, tool_context: ToolContext) -> dict:
    """Get the merchant's transactions of the last days, with the decline code and reason of declined ones.

    Args:
        days: How many days back to look, from 1 to 30.

    Returns:
        The transactions, newest first.
    """
    customer = _customer(tool_context)
    if customer is None:
        return {"error": "Merchant not found."}
    days = max(1, min(int(days), 30))
    today = date.today()
    rows = [
        {**{k: v for k, v in item.items() if k != "day_offset"}, "date": _sale_date(item, today).isoformat()}
        for item in customer["transactions"]
        if -days <= item["day_offset"] <= 0
    ]
    return {"transactions": sorted(rows, key=lambda r: (r["date"], r["time"]), reverse=True)}
