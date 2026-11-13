"""Start the API: POST /chat and the conversation for merchants, the ticket queue for operators."""

import hashlib
import hmac
import logging
import os
from dataclasses import asdict

from dotenv import load_dotenv

load_dotenv()  # before the agents read AGENT_MODEL and the API key

import uvicorn  # noqa: E402
from fastapi import Depends, HTTPException  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agents.getnet import store  # noqa: E402
from agents.getnet.chat import PUBLIC_FIELDS, SessionNotFound, answer_ticket, chat, conversation  # noqa: E402
from agents.getnet.guardrails import MAX_MESSAGE_CHARS  # noqa: E402
from agents.getnet.tools import handoff  # noqa: E402
from agents.getnet.tools.customer import customers  # noqa: E402
from agents.getnet.tools.kb_search import load_index  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for noisy in ("LiteLLM", "litellm", "httpx", "google_adk", "google_genai", "bm25s"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))  # messages per merchant per minute
OPEN_PATHS = {"/chat", "/chat/{session_id}", "/tickets", "/tickets/{number}/answer", "/health", "/docs", "/openapi.json"}

# The ADK app gives OpenTelemetry for every request. Its own routes (/run, sessions) have no authentication,
# so only ours stay; `make web` starts the ADK dev UI for local work.
app = get_fast_api_app(agents_dir="agents", web=False, use_local_storage=False)
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) in OPEN_PATHS]

bearer = HTTPBearer(auto_error=False)


def merchant(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    """The merchant of the token. In production, the Getnet app's login issues the token."""
    if credentials:
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        for user_id, customer in customers().items():
            if hmac.compare_digest(digest, customer["token_sha256"]):
                return user_id
    raise HTTPException(401, "A valid merchant token is required.", headers={"WWW-Authenticate": "Bearer"})


def operator(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    token = os.getenv("OPERATOR_TOKEN", "")
    if not token:
        raise HTTPException(503, "The operator API is off: set OPERATOR_TOKEN.")
    if not credentials or not hmac.compare_digest(credentials.credentials, token):
        raise HTTPException(401, "A valid operator token is required.", headers={"WWW-Authenticate": "Bearer"})


async def rate_limit(user_id: str) -> None:
    """At most RATE_LIMIT messages a minute for each merchant, in the database, so every API replica counts them."""
    if not await store.allow(user_id, RATE_LIMIT):
        raise HTTPException(429, "Too many messages. Wait a minute.", headers={"Retry-After": "60"})


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    user_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class TicketAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


@app.post("/chat")
async def chat_endpoint(request: ChatRequest, user_id: str = Depends(merchant)) -> dict:
    """Send a merchant message. Send the `session_id` of the reply to continue the same conversation."""
    if request.user_id != user_id:
        raise HTTPException(403, "The user_id is not the merchant of the token.")
    await rate_limit(user_id)
    try:
        response = await chat(request.message.strip(), user_id, request.session_id)
    except SessionNotFound:
        raise HTTPException(404, "No conversation with this session_id for this merchant.")
    return {name: value for name, value in asdict(response).items() if name in PUBLIC_FIELDS}


@app.get("/chat/{session_id}")
async def conversation_endpoint(session_id: str, user_id: str = Depends(merchant)) -> dict:
    """The messages of a conversation, also the answers of a person to its tickets."""
    try:
        return {"session_id": session_id, "messages": await conversation(user_id, session_id)}
    except SessionNotFound:
        raise HTTPException(404, "No conversation with this session_id for this merchant.")


@app.get("/tickets", dependencies=[Depends(operator)])
async def tickets_endpoint(status: str | None = None) -> list[dict]:
    """The ticket queue, for Getnet support operators. `status`: open or answered."""
    return await handoff.list_tickets(status)


@app.post("/tickets/{number}/answer", dependencies=[Depends(operator)])
async def answer_endpoint(number: str, body: TicketAnswer) -> dict:
    """An operator answers a ticket. The answer goes into the merchant's conversation."""
    ticket = await answer_ticket(number, body.answer.strip())
    if ticket is None:
        raise HTTPException(404, "No open ticket with this number.")
    return ticket


if __name__ == "__main__":
    load_index()
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
