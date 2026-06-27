"""Справочники (для F1/F7) и админ-операции (F9).

Включает загрузку расписания групп из CSV (на MVP координатор заливает
таблицу раз в неделю — раздел 8 ТЗ).
"""
from __future__ import annotations

import csv
import io
from datetime import time

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ClassSchedule,
    Curator,
    Department,
    Event,
    EventStatus,
    Group,
    ProtectedWindow,
    Role,
    Tag,
    User,
)
from app.schemas import (
    CuratorCreateIn,
    CuratorOut,
    DepartmentOut,
    GroupCreateIn,
    GroupOut,
    ImportSummaryOut,
    ProtectedWindowIn,
    ProtectedWindowOut,
    SimpleOk,
    TagOut,
)

# ---------- разбор значений ----------
_WEEKDAYS = {
    "пн": 0, "пон": 0, "понедельник": 0, "mon": 0, "monday": 0,
    "вт": 1, "вторник": 1, "tue": 1, "tuesday": 1,
    "ср": 2, "среда": 2, "wed": 2, "wednesday": 2,
    "чт": 3, "четверг": 3, "thu": 3, "thursday": 3,
    "пт": 4, "пятница": 4, "fri": 4, "friday": 4,
    "сб": 5, "суббота": 5, "sat": 5, "saturday": 5,
    "вс": 6, "воскресенье": 6, "sun": 6, "sunday": 6,
}


def parse_weekday(raw: str) -> int:
    raw = (raw or "").strip().lower()
    if raw.isdigit():
        n = int(raw)
        if 0 <= n <= 6:
            return n
        if n == 7:  # 1=Пн..7=Вс
            return 6
        if 1 <= n <= 7:
            return n - 1
        raise ValueError(f"неверный день недели: {raw}")
    if raw in _WEEKDAYS:
        return _WEEKDAYS[raw]
    raise ValueError(f"неверный день недели: {raw}")


def parse_time(raw: str) -> time:
    raw = (raw or "").strip().replace(".", ":").replace(",", ":")
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"неверное время: {raw}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"неверное время: {raw}")
    return time(h, m)


# ---------- справочники (чтение) ----------
async def list_departments(session: AsyncSession) -> list[DepartmentOut]:
    rows = await session.execute(select(Department).order_by(Department.name))
    return [DepartmentOut.model_validate(d) for d in rows.scalars()]


async def list_groups(
    session: AsyncSession, department_id: int | None = None
) -> list[GroupOut]:
    stmt = select(Group).order_by(Group.name)
    if department_id is not None:
        stmt = stmt.where(Group.department_id == department_id)
    rows = await session.execute(stmt)
    return [GroupOut.model_validate(g) for g in rows.scalars()]


async def list_tags(session: AsyncSession) -> list[TagOut]:
    rows = await session.execute(select(Tag).order_by(Tag.name))
    return [TagOut.model_validate(t) for t in rows.scalars()]


async def list_curators(session: AsyncSession) -> list[CuratorOut]:
    rows = await session.execute(select(Curator).order_by(Curator.full_name))
    curators = list(rows.scalars())
    dep_rows = await session.execute(select(Department))
    dep_names = {d.id: d.name for d in dep_rows.scalars()}
    return [
        CuratorOut(
            id=c.id,
            full_name=c.full_name,
            department_id=c.department_id,
            department_name=dep_names.get(c.department_id),
            contact=c.contact,
            note=c.note,
        )
        for c in curators
    ]


async def list_protected_windows(
    session: AsyncSession,
) -> list[ProtectedWindowOut]:
    rows = await session.execute(
        select(ProtectedWindow).order_by(
            ProtectedWindow.weekday, ProtectedWindow.start_time
        )
    )
    out = []
    for p in rows.scalars():
        out.append(
            ProtectedWindowOut(
                id=p.id,
                department_id=p.department_id,
                weekday=p.weekday,
                start_time=p.start_time.strftime("%H:%M"),
                end_time=p.end_time.strftime("%H:%M"),
                title=p.title,
            )
        )
    return out


# ---------- админ: создание справочников ----------
async def create_department(session: AsyncSession, name: str) -> DepartmentOut:
    d = Department(name=name.strip())
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return DepartmentOut.model_validate(d)


async def create_tag(session: AsyncSession, name: str) -> TagOut:
    name = name.strip()
    existing = (
        await session.execute(select(Tag).where(Tag.name == name))
    ).scalar_one_or_none()
    if existing:
        return TagOut.model_validate(existing)
    t = Tag(name=name)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return TagOut.model_validate(t)


async def create_group(session: AsyncSession, data: GroupCreateIn) -> GroupOut:
    if data.department_id is not None:
        if await session.get(Department, data.department_id) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "отделение не найдено")
    g = Group(
        name=data.name.strip(),
        direction=data.direction,
        department_id=data.department_id,
    )
    session.add(g)
    await session.commit()
    await session.refresh(g)
    return GroupOut.model_validate(g)


async def create_curator(
    session: AsyncSession, data: CuratorCreateIn
) -> CuratorOut:
    c = Curator(
        full_name=data.full_name.strip(),
        department_id=data.department_id,
        contact=data.contact.strip(),
        note=data.note,
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    dep = (
        await session.get(Department, c.department_id)
        if c.department_id
        else None
    )
    return CuratorOut(
        id=c.id,
        full_name=c.full_name,
        department_id=c.department_id,
        department_name=dep.name if dep else None,
        contact=c.contact,
        note=c.note,
    )


async def set_protected_window(
    session: AsyncSession, data: ProtectedWindowIn
) -> ProtectedWindowOut:
    p = ProtectedWindow(
        department_id=data.department_id,
        weekday=data.weekday,
        start_time=parse_time(data.start_time),
        end_time=parse_time(data.end_time),
        title=data.title or "Внеучебный час",
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return ProtectedWindowOut(
        id=p.id,
        department_id=p.department_id,
        weekday=p.weekday,
        start_time=p.start_time.strftime("%H:%M"),
        end_time=p.end_time.strftime("%H:%M"),
        title=p.title,
    )


# ---------- админ: роли и модерация ----------
async def grant_role(session: AsyncSession, tg_id: int, role: str) -> SimpleOk:
    # admin назначается только через ADMIN_TG_IDS — не через API (F9: доступ организаторам)
    if role not in {Role.STUDENT, Role.ORGANIZER}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "роль можно выдать только: student или organizer",
        )
    if tg_id <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "некорректный tg_id")
    user = (
        await session.execute(select(User).where(User.tg_id == tg_id))
    ).scalar_one_or_none()
    if user is None:
        user = User(tg_id=tg_id, role=role)
        session.add(user)
    else:
        user.role = role
    await session.commit()
    return SimpleOk(detail=f"роль {role} выдана tg_id={tg_id}")


async def events_for_moderation(session: AsyncSession) -> list[Event]:
    rows = await session.execute(
        select(Event)
        .where(Event.status == EventStatus.MODERATION)
        .options(selectinload(Event.tags), selectinload(Event.registrations))
        .order_by(Event.starts_at)
    )
    return list(rows.scalars())


async def moderate_event(
    session: AsyncSession, event_id: int, approve: bool
) -> SimpleOk:
    event = await session.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "мероприятие не найдено")
    event.status = EventStatus.PUBLISHED if approve else EventStatus.DRAFT
    await session.commit()
    return SimpleOk(detail="опубликовано" if approve else "отклонено")


# ---------- админ: импорт расписания из CSV (F9) ----------
def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        # эвристика для русского Excel
        return ";" if sample.count(";") > sample.count(",") else ","


def _norm(key: str) -> str:
    return (key or "").strip().lower().lstrip("﻿")


def _pick(row: dict[str, str], *names: str) -> str:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return ""


async def import_schedule_csv(
    session: AsyncSession, content: bytes
) -> ImportSummaryOut:
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    delimiter = _sniff_delimiter(sample)

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "пустой CSV-файл")

    summary = ImportSummaryOut()

    # имена групп → существующие/создаваемые
    existing_groups = {
        g.name: g for g in (await session.execute(select(Group))).scalars()
    }
    seen_group_ids: set[int] = set()
    seen_slots: set[tuple[int, int, time, time]] = set()  # дедуп строк CSV
    pending: list[tuple[int, int, time, time, str | None]] = []  # group_id,wd,s,e,title

    for i, raw_row in enumerate(reader, start=2):  # строка 1 — заголовок
        row = {_norm(k): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items()}
        group_name = _pick(row, "group", "группа", "группы")
        wd_raw = _pick(row, "weekday", "day", "день", "день недели")
        start_raw = _pick(row, "start", "начало", "from", "с")
        end_raw = _pick(row, "end", "конец", "to", "до")
        title = _pick(row, "title", "предмет", "пара", "subject", "name") or None

        if not group_name and not wd_raw and not start_raw and not end_raw:
            continue  # пустая строка
        try:
            if not group_name:
                raise ValueError("не указана группа")
            wd = parse_weekday(wd_raw)
            s = parse_time(start_raw)
            e = parse_time(end_raw)
            if e <= s:
                raise ValueError("конец раньше начала")
        except ValueError as exc:
            summary.skipped += 1
            summary.errors.append(f"строка {i}: {exc}")
            continue

        group = existing_groups.get(group_name)
        if group is None:
            group = Group(name=group_name)
            session.add(group)
            await session.flush()  # получить id
            existing_groups[group_name] = group
            summary.created_groups += 1

        key = (group.id, wd, s, e)
        if key in seen_slots:  # дубликат строки в файле
            summary.skipped += 1
            continue
        seen_slots.add(key)
        seen_group_ids.add(group.id)
        pending.append((group.id, wd, s, e, title))

    # «обновление расписания»: для затронутых групп заменяем целиком
    if seen_group_ids:
        await session.execute(
            delete(ClassSchedule).where(
                ClassSchedule.group_id.in_(seen_group_ids)
            )
        )
    for group_id, wd, s, e, title in pending:
        session.add(
            ClassSchedule(
                group_id=group_id,
                weekday=wd,
                start_time=s,
                end_time=e,
                title=title,
            )
        )
        summary.created_rows += 1

    await session.commit()
    return summary
