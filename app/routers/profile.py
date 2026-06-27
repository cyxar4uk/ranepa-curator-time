"""F1: профиль студента + справочники для онбординга."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import CurrentUser, SessionDep
from app.schemas import (
    DepartmentOut,
    GroupOut,
    MeOut,
    ProfileUpdate,
    TagOut,
)
from app.services import catalog, profile

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser, session: SessionDep) -> MeOut:
    return await profile.build_me(session, user)


@router.put("/profile", response_model=MeOut)
async def update_profile(
    data: ProfileUpdate, user: CurrentUser, session: SessionDep
) -> MeOut:
    return await profile.update_profile(session, user, data)


# --- справочники (нужны на онбординге и в формах) ---
@router.get("/refs/departments", response_model=list[DepartmentOut])
async def refs_departments(user: CurrentUser, session: SessionDep):
    return await catalog.list_departments(session)


@router.get("/refs/groups", response_model=list[GroupOut])
async def refs_groups(
    user: CurrentUser,
    session: SessionDep,
    department_id: Annotated[int | None, Query()] = None,
):
    return await catalog.list_groups(session, department_id)


@router.get("/refs/tags", response_model=list[TagOut])
async def refs_tags(user: CurrentUser, session: SessionDep):
    return await catalog.list_tags(session)
