import pytest

from agents.getnet import store


@pytest.fixture(autouse=True)
def ticket_db(tmp_path, monkeypatch):
    """Each test gets its own SQLite file for sessions, tickets and the rate limit."""
    path = tmp_path / "getnet.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    for var in ("OPERATOR_WEBHOOK_URL", "MERCHANT_WEBHOOK_URL", "WEBHOOK_SECRET"):
        monkeypatch.delenv(var, raising=False)
    store.engine.cache_clear()
    yield path
    store.engine.cache_clear()
