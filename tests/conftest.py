"""Тестовое окружение: sqlite, dev-режим, отдельный админ-tg_id."""
import os

# ВАЖНО: задаём окружение до импорта app.* (конфиг кэшируется при импорте)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_curator.db"
os.environ["DEV_MODE"] = "true"
os.environ["DEV_TG_ID"] = "100001"
os.environ["ADMIN_TG_IDS"] = "999001"
os.environ["BOT_TOKEN"] = "123:test-token"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture
async def client():
    from app.db import Base, SessionLocal, engine
    from app.main import app
    from app.seed import seed_if_empty

    # чистая схема на каждый тест
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_if_empty(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
