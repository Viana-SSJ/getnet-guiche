"""Human handoff: a ticket queue in the database. A person answers a ticket, and the answer goes into the merchant's chat."""

import logging
import re
from datetime import datetime

from google.adk.tools.tool_context import ToolContext
from sqlalchemy import insert, select, update

from .. import notify
from ..store import tickets, transaction

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _number(ticket_id: int) -> str:
    return f"HD-{ticket_id:05d}"


def _ticket(row) -> dict:
    return {"ticket": _number(row.id), **{k: v for k, v in row._asdict().items() if k != "id"}}


def _id(number: str) -> int:
    """HD-00042 is 42; anything else is 0, which is no ticket."""
    return int(number[3:]) if number.startswith("HD-") and number[3:].isdigit() else 0


async def open_ticket(user_id: str, session_id: str | None, reason: str, summary: str) -> str:
    """Open a ticket, tell the operators, and return its number. Also used by the fallback, without an LLM."""
    async with transaction() as db:
        result = await db.execute(insert(tickets).values(user_id=user_id, session_id=session_id, reason=reason,
                                                         summary=summary, status="open", opened_at=_now()))
    number = _number(result.inserted_primary_key[0])
    log.info("handoff ticket opened: %s", number)
    await notify.send("ticket.opened", await get_ticket(number))
    return number


async def list_tickets(status: str | None = None) -> list[dict]:
    query = select(tickets).order_by(tickets.c.id)
    if status:
        query = query.where(tickets.c.status == status)
    async with transaction() as db:
        return [_ticket(row) for row in await db.execute(query)]


async def get_ticket(number: str) -> dict | None:
    async with transaction() as db:
        row = (await db.execute(select(tickets).where(tickets.c.id == _id(number)))).first()
    return _ticket(row) if row else None


async def open_ticket_in(text: str, user_id: str, session_id: str) -> str | None:
    """The first ticket number in the text that is an open ticket of this merchant and this conversation."""
    for number in re.findall(r"HD-\d{5,}", text):
        ticket = await get_ticket(number)
        if ticket and (ticket["user_id"], ticket["session_id"], ticket["status"]) == (user_id, session_id, "open"):
            return number
    return None


async def answer_ticket(number: str, answer: str) -> dict | None:
    """Save a person's answer and close the ticket. Returns None if there is no open ticket with this number."""
    async with transaction() as db:
        answered = (await db.execute(update(tickets).where(tickets.c.id == _id(number), tickets.c.status == "open")
                                     .values(status="answered", answer=answer, answered_at=_now()))).rowcount
    return await get_ticket(number) if answered else None


async def create_ticket(reason: str, summary: str, tool_context: ToolContext) -> dict:
    """Open a ticket so that a person from Getnet support answers the merchant.

    Args:
        reason: Why a person is needed, in a few words.
        summary: A short summary of the merchant's request.

    Returns:
        The ticket number and where the answer comes.
    """
    # One ticket for one message: a model that calls again gets the same number.
    key = f"ticket.{tool_context.state.get('turn')}"
    if not (number := tool_context.state.get(key)):
        number = await open_ticket(tool_context.user_id, tool_context.session.id, reason, summary)
        tool_context.state[key] = number
    return {"ticket": number, "answer": "A person from Getnet support answers in this chat."}
