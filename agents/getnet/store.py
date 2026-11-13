"""The database of the sessions, the tickets and the rate limit.

One SQLite file by default, which is enough for one API process. Set DATABASE_URL to a Postgres URL
(postgresql+asyncpg://...) to run several API replicas on one database. The ADK session service, the
ticket queue and the rate limit share one engine.
"""

import os
import time
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, Text, delete, func, insert, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

DEFAULT_URL = "sqlite+aiosqlite:///var/getnet.db"

metadata = MetaData()
tickets = Table(
    "tickets", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String(64), nullable=False),
    Column("session_id", String(64)),
    Column("reason", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("status", String(16), nullable=False, default="open"),
    Column("answer", Text),
    Column("opened_at", String(32), nullable=False),
    Column("answered_at", String(32)),
)
rate_events = Table(
    "rate_events", metadata,
    Column("user_id", String(64), nullable=False, index=True),
    Column("at", Float, nullable=False, index=True),
)
_ready: set[AsyncEngine] = set()


@cache
def engine() -> AsyncEngine:
    url = make_url(os.getenv("DATABASE_URL", DEFAULT_URL))
    if url.get_backend_name() != "sqlite":
        return create_async_engine(url, pool_pre_ping=True)
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    # A new connection for each use: a SQLite file opens fast, and no connection crosses event loops.
    return create_async_engine(url, poolclass=NullPool)


@asynccontextmanager
async def transaction():
    """A connection in a transaction. The first use creates the tables."""
    db_engine = engine()
    if db_engine not in _ready:
        async with db_engine.begin() as db:
            await db.run_sync(metadata.create_all)
        _ready.add(db_engine)
    async with db_engine.begin() as db:
        yield db


async def allow(user_id: str, limit: int, window: float = 60) -> bool:
    """A sliding window of `limit` messages in `window` seconds for each merchant, which every replica shares.

    Two replicas can each let one more message through at the same moment: a limit against abuse, not a quota.
    """
    now = time.time()
    async with transaction() as db:
        await db.execute(delete(rate_events).where(rate_events.c.at < now - window))
        recent = (await db.execute(select(func.count()).where(rate_events.c.user_id == user_id))).scalar_one()
        if recent >= limit:
            return False
        await db.execute(insert(rate_events).values(user_id=user_id, at=now))
    return True

