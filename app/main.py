"""Точка входа FastAPI: API (F1–F9) + раздача Telegram Mini App."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import (
    admin,
    contacts,
    events,
    organizer,
    profile,
    schedule,
    tm,
)
from app.seed import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        await seed_if_empty(session)
    yield


app = FastAPI(title="Школа кураторов — бот", version="0.1.0", lifespan=lifespan)

# В dev фронт может отдаваться через туннель — разрешаем CORS свободно.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (profile, schedule, events, tm, contacts, organizer, admin):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "dev_mode": settings.dev_mode}


# Mini App (статика). Монтируем ПОСЛЕ роутеров, чтобы /api/* имел приоритет.
if FRONTEND_DIR.exists():
    app.mount(
        "/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend"
    )
