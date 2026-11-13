"""Webhooks: the systems of Getnet learn of a ticket at once, and need not ask the queue again and again.

- OPERATOR_WEBHOOK_URL gets `ticket.opened`: the support team's tool, or a chat (Slack, Telegram) through a relay.
- MERCHANT_WEBHOOK_URL gets `ticket.answered`: the back end of the Getnet app, which sends the merchant a push
  notification with the person's answer. The merchant does not have to send a new message to see it.

Each request has the header `X-Signature: sha256=<HMAC-SHA256 of the body with WEBHOOK_SECRET>`, so the receiver
can check that it comes from this service. A failed delivery is only logged: the queue (GET /tickets) and the
conversation (GET /chat/{session_id}) still have everything.
"""

import hashlib
import hmac
import json
import logging
import os

import httpx

log = logging.getLogger(__name__)
URLS = {"ticket.opened": "OPERATOR_WEBHOOK_URL", "ticket.answered": "MERCHANT_WEBHOOK_URL"}
TIMEOUT = 3  # seconds: a slow receiver must not hold the merchant's answer


def signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def send(event: str, ticket: dict) -> bool:
    """POST the event and the ticket to its webhook, if one is set. True if the receiver accepted it."""
    url = os.getenv(URLS[event])
    if not url:
        return False
    body = json.dumps({"event": event, **ticket}, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if secret := os.getenv("WEBHOOK_SECRET"):
        headers["X-Signature"] = signature(body, secret)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            (await client.post(url, content=body, headers=headers)).raise_for_status()
    except httpx.HTTPError as error:
        log.warning("webhook %s for %s failed: %r", event, ticket.get("ticket"), error)
        return False
    return True
