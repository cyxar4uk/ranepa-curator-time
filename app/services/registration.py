"""F5: запись на мероприятие + фиксация подсветки пересечений."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventStatus, RegStatus, Registration, User
from app.schemas import RegistrationResultOut, SimpleOk
from app.services import schedule


async def _registered_count(session: AsyncSession, event_id: int) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegStatus.REGISTERED,
            )
        )
    ).scalar_one()


async def register(
    session: AsyncSession, user: User, event_id: int
) -> RegistrationResultOut:
    # запись — обработка ПД: требуем согласие (F1, 152-ФЗ)
    if user.consent_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "требуется согласие на обработку персональных данных",
        )

    event = await session.get(Event, event_id)
    if event is None or event.status != EventStatus.PUBLISHED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "мероприятие не найдено")

    reg = (
        await session.execute(
            select(Registration).where(
                Registration.user_id == user.id,
                Registration.event_id == event_id,
            )
        )
    ).scalar_one_or_none()
    already = reg is not None and reg.status == RegStatus.REGISTERED

    if event.capacity is not None and not already:
        count = await _registered_count(session, event_id)
        if count >= event.capacity:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Свободных мест больше нет"
            )

    # F5: проверяем пересечение и сохраняем подсветку «как было на момент записи»
    conflict = await schedule.check_conflict(
        session, user, event.starts_at, event.ends_at
    )

    if reg is None:
        reg = Registration(
            user_id=user.id,
            event_id=event_id,
            status=RegStatus.REGISTERED,
            conflict_note=conflict.message,
        )
        session.add(reg)
    else:
        reg.status = RegStatus.REGISTERED
        reg.conflict_note = conflict.message

    await session.commit()
    await session.refresh(reg)
    return RegistrationResultOut(
        registration_id=reg.id, status=reg.status, conflict=conflict
    )


async def cancel(session: AsyncSession, user: User, event_id: int) -> SimpleOk:
    reg = (
        await session.execute(
            select(Registration).where(
                Registration.user_id == user.id,
                Registration.event_id == event_id,
            )
        )
    ).scalar_one_or_none()
    if reg is None or reg.status != RegStatus.REGISTERED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "запись не найдена")
    reg.status = RegStatus.CANCELLED
    await session.commit()
    return SimpleOk(detail="запись отменена")
