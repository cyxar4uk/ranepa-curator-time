"""F8: кабинет организатора."""
from __future__ import annotations

from fastapi import APIRouter

from app.deps import Organizer, SessionDep
from app.schemas import EventCardOut, EventCreateIn, EventUpdateIn
from app.services import organizer as organizer_service

router = APIRouter(prefix="/api/organizer", tags=["organizer"])


@router.get("/events", response_model=list[EventCardOut])
async def my_events(user: Organizer, session: SessionDep):
    return await organizer_service.list_own_events(session, user)


@router.post("/events", response_model=EventCardOut)
async def create_event(
    data: EventCreateIn, user: Organizer, session: SessionDep
) -> EventCardOut:
    return await organizer_service.create_event(session, user, data)


@router.put("/events/{event_id}", response_model=EventCardOut)
async def update_event(
    event_id: int, data: EventUpdateIn, user: Organizer, session: SessionDep
) -> EventCardOut:
    return await organizer_service.update_event(session, user, event_id, data)
