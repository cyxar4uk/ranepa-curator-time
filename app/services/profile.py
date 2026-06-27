"""F1: онбординг и профиль студента."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Group, Tag, User, user_interests
from app.schemas import DepartmentOut, GroupOut, MeOut, ProfileUpdate, TagOut


async def build_me(session: AsyncSession, user: User) -> MeOut:
    group: GroupOut | None = None
    department: DepartmentOut | None = None

    if user.group_id:
        g = await session.get(Group, user.group_id)
        if g:
            group = GroupOut.model_validate(g)
            if g.department_id:
                d = await session.get(Department, g.department_id)
                if d:
                    department = DepartmentOut.model_validate(d)

    rows = await session.execute(
        select(Tag)
        .join(user_interests, Tag.id == user_interests.c.tag_id)
        .where(user_interests.c.user_id == user.id)
        .order_by(Tag.name)
    )
    interests = [TagOut.model_validate(t) for t in rows.scalars()]

    return MeOut(
        tg_id=user.tg_id,
        full_name=user.full_name,
        role=user.role,
        group=group,
        department=department,
        interests=interests,
        goal=user.goal,
        has_consent=user.consent_at is not None,
        has_profile=user.has_profile,
    )


async def update_profile(
    session: AsyncSession, user: User, data: ProfileUpdate
) -> MeOut:
    # 1) Согласие на ПД (F1, 152-ФЗ) обрабатываем первым.
    if data.consent is False:
        # отзыв согласия: снимаем отметку и обезличиваем связанные ПД
        user.consent_at = None
        user.goal = None
        await session.execute(
            delete(user_interests).where(user_interests.c.user_id == user.id)
        )
        await session.commit()
        await session.refresh(user)
        return await build_me(session, user)

    if data.consent is True and user.consent_at is None:
        user.consent_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # 2) Без согласия не сохраняем содержательные ПД.
    wants_pd = (
        data.group_id is not None
        or data.goal is not None
        or data.interest_ids is not None
    )
    if wants_pd and user.consent_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "требуется согласие на обработку персональных данных",
        )

    # 3) Запись полей профиля.
    if data.group_id is not None:
        g = await session.get(Group, data.group_id)
        if g is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "группа не найдена")
        user.group_id = data.group_id

    if data.goal is not None:
        user.goal = data.goal.strip() or None

    if data.interest_ids is not None:
        await session.execute(
            delete(user_interests).where(user_interests.c.user_id == user.id)
        )
        if data.interest_ids:
            valid = list(
                (
                    await session.execute(
                        select(Tag.id).where(Tag.id.in_(data.interest_ids))
                    )
                ).scalars()
            )
            for tag_id in valid:
                await session.execute(
                    insert(user_interests).values(user_id=user.id, tag_id=tag_id)
                )

    await session.commit()
    await session.refresh(user)
    return await build_me(session, user)
