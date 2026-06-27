"""F3 (лента), F4 (карточка ценности), F5 (запись + пересечения)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import CurrentUser, SessionDep
from app.schemas import (
    EventCardOut,
    EventDetailOut,
    RegistrationResultOut,
    SimpleOk,
)
from app.services import feed, registration

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=list[EventCardOut])
async def list_events(
    user: CurrentUser,
    session: SessionDep,
    by_interests: Annotated[bool, Query()] = True,
    tag_id: Annotated[list[int] | None, Query()] = None,
    include_past: Annotated[bool, Query()] = False,
):
    return await feed.list_events(
        session,
        user,
        by_interests=by_interests,
        tag_ids=tag_id,
        include_past=include_past,
    )


@router.get("/events/{event_id}", response_model=EventDetailOut)
async def event_detail(
    event_id: int, user: CurrentUser, session: SessionDep
) -> EventDetailOut:
    return await feed.get_event_detail(session, user, event_id)


@router.post("/events/{event_id}/register", response_model=RegistrationResultOut)
async def register(
    event_id: int, user: CurrentUser, session: SessionDep
) -> RegistrationResultOut:
    return await registration.register(session, user, event_id)


@router.post("/events/{event_id}/cancel", response_model=SimpleOk)
async def cancel(event_id: int, user: CurrentUser, session: SessionDep) -> SimpleOk:
    return await registration.cancel(session, user, event_id)
