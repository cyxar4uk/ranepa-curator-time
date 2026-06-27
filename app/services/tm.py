"""F6: программа тайм-менеджмента (карточки «3 горизонта» и «Учебные цели»)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TMCard, TMProgress, User
from app.schemas import TMCardOut


async def list_cards(session: AsyncSession, user: User) -> list[TMCardOut]:
    cards = list(
        (
            await session.execute(
                select(TMCard).order_by(TMCard.order, TMCard.id)
            )
        ).scalars()
    )
    progress = {
        p.card_id: p
        for p in (
            await session.execute(
                select(TMProgress).where(TMProgress.user_id == user.id)
            )
        ).scalars()
    }
    out: list[TMCardOut] = []
    for c in cards:
        p = progress.get(c.id)
        out.append(
            TMCardOut(
                id=c.id,
                module=c.module,
                title=c.title,
                content=c.content,
                task=c.task,
                order=c.order,
                completed=p is not None,
                answer=p.answer if p else None,
            )
        )
    return out


async def complete_card(
    session: AsyncSession, user: User, card_id: int, answer: str | None
) -> TMCardOut:
    card = await session.get(TMCard, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "карточка не найдена")

    p = (
        await session.execute(
            select(TMProgress).where(
                TMProgress.user_id == user.id, TMProgress.card_id == card_id
            )
        )
    ).scalar_one_or_none()

    clean = (answer or "").strip() or None
    if p is None:
        session.add(TMProgress(user_id=user.id, card_id=card_id, answer=clean))
    else:
        p.answer = clean
        p.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.commit()
    return TMCardOut(
        id=card.id,
        module=card.module,
        title=card.title,
        content=card.content,
        task=card.task,
        order=card.order,
        completed=True,
        answer=clean,
    )
