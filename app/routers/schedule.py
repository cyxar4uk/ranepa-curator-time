"""F2: свободные часы на скользящую неделю + защищённое окно."""
from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import WeekOut
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api", tags=["schedule"])


@router.get("/schedule/week", response_model=WeekOut)
async def week(user: CurrentUser, session: SessionDep) -> WeekOut:
    return await schedule_service.compute_week(session, user)
