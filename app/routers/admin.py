"""F9: админ — расписание (CSV), справочники, защищённое окно, модерация, роли."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.deps import Admin, SessionDep
from app.schemas import (
    CuratorCreateIn,
    CuratorOut,
    DepartmentOut,
    EventCardOut,
    GrantRoleIn,
    GroupCreateIn,
    GroupOut,
    ImportSummaryOut,
    ModerationIn,
    NameIn,
    ProtectedWindowIn,
    ProtectedWindowOut,
    SimpleOk,
    TagOut,
)
from app.services import catalog
from app.services.feed import to_card

router = APIRouter(prefix="/api/admin", tags=["admin"])

MAX_CSV_BYTES = 2 * 1024 * 1024  # 2 МБ достаточно для расписания групп


# --- справочники ---
@router.post("/departments", response_model=DepartmentOut)
async def create_department(data: NameIn, admin: Admin, session: SessionDep):
    return await catalog.create_department(session, data.name)


@router.post("/tags", response_model=TagOut)
async def create_tag(data: NameIn, admin: Admin, session: SessionDep):
    return await catalog.create_tag(session, data.name)


@router.post("/groups", response_model=GroupOut)
async def create_group(data: GroupCreateIn, admin: Admin, session: SessionDep):
    return await catalog.create_group(session, data)


@router.post("/curators", response_model=CuratorOut)
async def create_curator(data: CuratorCreateIn, admin: Admin, session: SessionDep):
    return await catalog.create_curator(session, data)


# --- защищённое окно ---
@router.get("/protected-windows", response_model=list[ProtectedWindowOut])
async def list_protected(admin: Admin, session: SessionDep):
    return await catalog.list_protected_windows(session)


@router.post("/protected-windows", response_model=ProtectedWindowOut)
async def add_protected(
    data: ProtectedWindowIn, admin: Admin, session: SessionDep
):
    return await catalog.set_protected_window(session, data)


# --- роли (выдача доступа организаторам) ---
@router.post("/grant-role", response_model=SimpleOk)
async def grant_role(data: GrantRoleIn, admin: Admin, session: SessionDep):
    return await catalog.grant_role(session, data.tg_id, data.role)


# --- модерация мероприятий ---
@router.get("/moderation", response_model=list[EventCardOut])
async def moderation_queue(admin: Admin, session: SessionDep):
    events = await catalog.events_for_moderation(session)
    return [to_card(e, set()) for e in events]


@router.post("/moderation/{event_id}", response_model=SimpleOk)
async def moderate(
    event_id: int, data: ModerationIn, admin: Admin, session: SessionDep
):
    return await catalog.moderate_event(session, event_id, data.approve)


# --- загрузка расписания групп (CSV) ---
@router.post("/schedule/import", response_model=ImportSummaryOut)
async def import_schedule(
    admin: Admin,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
):
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "файл слишком большой (макс. 2 МБ)",
        )
    return await catalog.import_schedule_csv(session, content)
