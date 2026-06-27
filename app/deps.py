"""FastAPI-зависимости: текущий пользователь и ролевые гейты.

Авторизация: фронт Mini App передаёт initData в заголовке
`X-Telegram-Init-Data`. В DEV_MODE проверка подписи пропускается и
пользователь определяется по DEV_TG_ID (или заголовку `X-Dev-Tg-Id`,
чтобы удобно отлаживать роли).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Role, User
from app.security import InitDataError, TgUser, parse_and_validate


async def _resolve_tg_user(
    init_data: str | None,
    dev_tg_id: str | None,
) -> TgUser:
    if settings.dev_mode:
        # в dev допускаем как валидный initData, так и упрощённый вход
        if init_data:
            try:
                return parse_and_validate(init_data, settings.bot_token)
            except InitDataError:
                pass
        tg_id = settings.dev_tg_id
        if dev_tg_id and dev_tg_id.strip().lstrip("-").isdigit():
            tg_id = int(dev_tg_id.strip())
        return TgUser(tg_id=tg_id, full_name="Dev User", username="dev")

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Telegram-Init-Data header is required",
        )
    try:
        return parse_and_validate(init_data, settings.bot_token)
    except InitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid init data: {exc}",
        ) from exc


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    x_dev_tg_id: Annotated[str | None, Header()] = None,
) -> User:
    tg = await _resolve_tg_user(x_telegram_init_data, x_dev_tg_id)

    user = (
        await session.execute(select(User).where(User.tg_id == tg.tg_id))
    ).scalar_one_or_none()

    if user is None:
        user = User(tg_id=tg.tg_id, full_name=tg.full_name, username=tg.username)
        session.add(user)
    else:
        # обновляем отображаемые данные из Telegram
        if tg.full_name:
            user.full_name = tg.full_name
        if tg.username:
            user.username = tg.username

    # автоповышение администраторов из ADMIN_TG_IDS
    if tg.tg_id in settings.admin_ids and user.role != Role.ADMIN:
        user.role = Role.ADMIN

    await session.commit()
    await session.refresh(user)
    return user


SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _is_at_least(user: User, *allowed: str) -> bool:
    # админ имеет права организатора
    if user.role == Role.ADMIN:
        return True
    return user.role in allowed


async def require_organizer(user: CurrentUser) -> User:
    if not _is_at_least(user, Role.ORGANIZER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="нужны права организатора",
        )
    return user


async def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="нужны права администратора",
        )
    return user


Organizer = Annotated[User, Depends(require_organizer)]
Admin = Annotated[User, Depends(require_admin)]
