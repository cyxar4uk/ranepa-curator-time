"""F8: кабинет организатора (создание/редактирование своих мероприятий)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Event, EventStatus, Role, Tag, User
from app.schemas import EventCardOut, EventCreateIn, EventUpdateIn
from app.services.feed import to_card


async def _load_card(session: AsyncSession, event_id: int) -> EventCardOut:
    event = (
        await session.execute(
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.tags), selectinload(Event.registrations))
        )
    ).scalar_one()
    return to_card(event, set())


async def _resolve_tags(session: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    rows = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    return list(rows.scalars())


def _can_edit(user: User, event: Event) -> bool:
    return user.role == Role.ADMIN or event.organizer_id == user.id


async def create_event(
    session: AsyncSession, organizer: User, data: EventCreateIn
) -> EventCardOut:
    if data.ends_at <= data.starts_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "время окончания раньше начала"
        )
    status_value = (
        EventStatus.MODERATION
        if settings.require_moderation and organizer.role != Role.ADMIN
        else EventStatus.PUBLISHED
    )
    event = Event(
        title=data.title.strip(),
        description=data.description,
        organizer_id=organizer.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        location=data.location,
        value_skill=data.value_skill,
        value_points=data.value_points or 0,
        value_portfolio=data.value_portfolio,
        capacity=data.capacity,
        status=status_value,
    )
    event.tags = await _resolve_tags(session, data.tag_ids)
    session.add(event)
    await session.commit()
    return await _load_card(session, event.id)


async def update_event(
    session: AsyncSession, organizer: User, event_id: int, data: EventUpdateIn
) -> EventCardOut:
    # eager-загрузка tags: присваивание event.tags на персистентном объекте
    # иначе инициирует ленивую загрузку коллекции вне greenlet (MissingGreenlet)
    event = (
        await session.execute(
            select(Event).where(Event.id == event_id).options(selectinload(Event.tags))
        )
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "мероприятие не найдено")
    if not _can_edit(organizer, event):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "это не ваше мероприятие")

    fields = data.model_dump(exclude_unset=True)
    if "tag_ids" in fields:
        event.tags = await _resolve_tags(session, fields.pop("tag_ids") or [])
    for key, value in fields.items():
        setattr(event, key, value)

    if event.ends_at <= event.starts_at:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "время окончания раньше начала"
        )

    await session.commit()
    return await _load_card(session, event.id)


async def list_own_events(
    session: AsyncSession, organizer: User
) -> list[EventCardOut]:
    stmt = (
        select(Event)
        .options(selectinload(Event.tags), selectinload(Event.registrations))
        .order_by(Event.starts_at.desc())
    )
    if organizer.role != Role.ADMIN:
        stmt = stmt.where(Event.organizer_id == organizer.id)
    events = list((await session.execute(stmt)).scalars())
    return [to_card(e, set()) for e in events]
