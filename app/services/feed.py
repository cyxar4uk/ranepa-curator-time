"""F3 (лента по интересам/тегам) и F4 (карточки ценности)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import campus_now

from app.models import (
    Event,
    EventStatus,
    RegStatus,
    Registration,
    User,
    user_interests,
)
from app.schemas import EventCardOut, EventDetailOut, TagOut, ValueOut
from app.services import schedule


async def user_interest_ids(session: AsyncSession, user: User) -> set[int]:
    rows = await session.execute(
        select(user_interests.c.tag_id).where(user_interests.c.user_id == user.id)
    )
    return set(rows.scalars())


async def user_registered_event_ids(session: AsyncSession, user: User) -> set[int]:
    rows = await session.execute(
        select(Registration.event_id).where(
            Registration.user_id == user.id,
            Registration.status == RegStatus.REGISTERED,
        )
    )
    return set(rows.scalars())


def registered_count(event: Event) -> int:
    return sum(1 for r in event.registrations if r.status == RegStatus.REGISTERED)


def to_card(event: Event, registered_ids: set[int], conflict=None) -> EventCardOut:
    return EventCardOut(
        id=event.id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        tags=[TagOut(id=t.id, name=t.name) for t in event.tags],
        value=ValueOut(
            skill=event.value_skill,
            points=event.value_points,
            portfolio=event.value_portfolio,
        ),
        capacity=event.capacity,
        registered_count=registered_count(event),
        is_registered=event.id in registered_ids,
        status=event.status,
        conflict=conflict,
    )


async def list_events(
    session: AsyncSession,
    user: User,
    *,
    by_interests: bool = True,
    tag_ids: list[int] | None = None,
    include_past: bool = False,
) -> list[EventCardOut]:
    stmt = (
        select(Event)
        .where(Event.status == EventStatus.PUBLISHED)
        .options(selectinload(Event.tags), selectinload(Event.registrations))
        .order_by(Event.starts_at)
    )
    if not include_past:
        stmt = stmt.where(Event.starts_at >= campus_now())

    events = list((await session.execute(stmt)).scalars())
    registered_ids = await user_registered_event_ids(session, user)

    tagset = set(tag_ids or [])
    if tagset:
        # явный фильтр по тегам имеет приоритет над «по интересам»
        events = [e for e in events if any(t.id in tagset for t in e.tags)]
    elif by_interests:
        interest_ids = await user_interest_ids(session, user)
        if interest_ids:
            events = [e for e in events if any(t.id in interest_ids for t in e.tags)]

    # вписываемость считаем батчем: контекст расписания грузим один раз
    classes, protected, has_group = await schedule.load_schedule_context(session, user)
    return [
        to_card(
            e,
            registered_ids,
            schedule.conflict_for(classes, protected, has_group, e.starts_at, e.ends_at),
        )
        for e in events
    ]


async def get_event_detail(
    session: AsyncSession, user: User, event_id: int
) -> EventDetailOut:
    event = (
        await session.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(
                selectinload(Event.tags),
                selectinload(Event.registrations),
                selectinload(Event.organizer),
            )
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "мероприятие не найдено")

    registered_ids = await user_registered_event_ids(session, user)
    card = to_card(event, registered_ids)

    conflict = await schedule.check_conflict(
        session, user, event.starts_at, event.ends_at
    )
    my_reg = next(
        (
            r
            for r in event.registrations
            if r.user_id == user.id and r.status == RegStatus.REGISTERED
        ),
        None,
    )

    return EventDetailOut(
        **card.model_dump(exclude={"conflict"}),
        description=event.description,
        organizer_name=event.organizer.full_name if event.organizer else None,
        conflict=conflict,
        my_conflict_note=my_reg.conflict_note if my_reg else None,
    )
