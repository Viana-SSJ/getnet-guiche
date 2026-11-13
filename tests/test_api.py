import asyncio
import re
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from agents.getnet import store
from agents.getnet.chat import ChatResponse, SessionNotFound

MERCHANT = {"Authorization": "Bearer demo-token-cliente1988"}
OPERATOR = {"Authorization": "Bearer operator-secret"}


@pytest.fixture
def client(monkeypatch):
    async def fake_chat(message, user_id, session_id=None):
        if session_id == "unknown":
            raise SessionNotFound(session_id)
        return ChatResponse(answer=f"{user_id}: {message}", session_id=session_id or "new", evidence=[{"tool": "x"}])

    monkeypatch.setattr(main, "chat", fake_chat)
    monkeypatch.setenv("OPERATOR_TOKEN", "operator-secret")
    return TestClient(main.app)


def send(client, headers=MERCHANT, **body):
    return client.post("/chat", headers=headers, json={"message": " Oi ", "user_id": "cliente1988", **body})


def test_chat_endpoint_returns_the_reply_contract(client):
    reply = send(client)
    assert reply.status_code == 200
    body = reply.json()
    assert (body["answer"], body["session_id"]) == ("cliente1988: Oi", "new")
    assert set(body) == {"answer", "tag", "tag_confidence", "agents_used", "tools_used", "sources", "handoff", "ticket", "masked",
                         "replanned", "fallback", "session_id", "model", "latency_ms", "request_id"}


def test_chat_needs_the_token_of_the_same_merchant(client):
    assert send(client, headers={}).status_code == 401
    assert send(client, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert send(client, user_id="cliente2000").status_code == 403
    assert send(client, headers={"Authorization": "Bearer demo-token-cliente2000"}, user_id="cliente2000").status_code == 200


def test_chat_endpoint_validates_input(client):
    assert send(client, message="").status_code == 422
    assert send(client, user_id="../etc").status_code == 422
    assert send(client, session_id="a/b").status_code == 422
    assert send(client, session_id="unknown").status_code == 404


def test_each_merchant_has_a_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 2)
    assert [send(client).status_code for _ in range(3)] == [200, 200, 429]
    assert send(client, headers={"Authorization": "Bearer demo-token-cliente2000"}, user_id="cliente2000").status_code == 200


def test_the_rate_limit_is_shared_by_every_api_replica():
    assert [asyncio.run(store.allow("cliente1988", 2)) for _ in range(2)] == [True, True]
    store.engine.cache_clear()  # another process: a new engine on the same database
    assert asyncio.run(store.allow("cliente1988", 2)) is False


def test_the_operator_api_needs_the_operator_token(client, monkeypatch):
    assert client.get("/tickets").status_code == 401
    assert client.get("/tickets", headers=MERCHANT).status_code == 401
    assert client.get("/tickets", headers=OPERATOR).json() == []
    assert client.post("/tickets/HD-00001/answer", headers=OPERATOR, json={"answer": "Feito"}).status_code == 404
    monkeypatch.delenv("OPERATOR_TOKEN")
    assert client.get("/tickets", headers=OPERATOR).status_code == 503


def test_the_adk_routes_without_authentication_are_off(client):
    assert client.get("/list-apps").status_code == 404
    assert client.post("/run", json={}).status_code == 404
    assert client.get("/health").status_code == 200


def test_dependencies_are_pinned():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    groups = project["dependency-groups"].values()
    for requirement in [*project["project"]["dependencies"], *(r for group in groups for r in group)]:
        assert re.fullmatch(r"[A-Za-z0-9_.\[\]-]+==[0-9][0-9A-Za-z.]*", requirement), requirement
