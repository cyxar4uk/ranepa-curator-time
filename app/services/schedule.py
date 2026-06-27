"""F2 (свободные часы + защищённое окно) и F5 (детекция пересечений).

Ключевая идея стратегии: считаем НЕ персональную занятость, а свободные
часы на уровне ГРУППЫ. Расписание пар — еженедельное (по дню недели),
горизонт — скользящая неделя от сегодня.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import campus_now, settings
from app.models import ClassSchedule, Group, ProtectedWindow, User
from app.schemas import BusyOut, ConflictOut, DayOut, IntervalOut, WeekOut

WEEKDAY_FULL = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]
WEEKDAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# ---------- чистые помощники (легко тестируются) ----------
def to_min(t: time) -> int:
    return t.hour * 60 + t.minute


def to_hhmm(minutes: int) -> str:
    minutes = max(0, min(24 * 60, minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Пересекаются ли [a) и [b)? Касание границами не считается."""
    return a_start < b_end and b_start < a_end


def free_intervals(
    day_start: int, day_end: int, busy: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Свободные окна = [day_start, day_end] минус занятые интервалы."""
    # нормализуем и сливаем занятые, обрезая по границам дня
    clipped: list[tuple[int, int]] = []
    for s, e in busy:
        s, e = max(s, day_start), min(e, day_end)
        if s < e:
            clipped.append((s, e))
    clipped.sort()

    merged: list[tuple[int, int]] = []
    for s, e in clipped:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    free: list[tuple[int, int]] = []
    cursor = day_start
    for s, e in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < day_end:
        free.append((cursor, day_end))
    return free


# ---------- доступ к данным ----------
async def _department_id_for(session: AsyncSession, user: User) -> int | None:
    if not user.group_id:
        return None
    group = await session.get(Group, user.group_id)
    return group.department_id if group else None


async def _load_protected(
    session: AsyncSession, department_id: int | None
) -> list[ProtectedWindow]:
    """Глобальные окна (department_id IS NULL) + окна отделения студента."""
    cond = ProtectedWindow.department_id.is_(None)
    if department_id is not None:
        cond = or_(cond, ProtectedWindow.department_id == department_id)
    rows = await session.execute(select(ProtectedWindow).where(cond))
    return list(rows.scalars())


# ---------- F2: неделя свободных часов ----------
async def compute_week(
    session: AsyncSession, user: User, today: date | None = None
) -> WeekOut:
    today = today or campus_now().date()
    day_start = to_min(settings.day_start_time)
    day_end = to_min(settings.day_end_time)

    department_id = await _department_id_for(session, user)
    protected = await _load_protected(session, department_id)

    classes: list[ClassSchedule] = []
    group_name = None
    if user.group_id:
        group = await session.get(Group, user.group_id)
        group_name = group.name if group else None
        rows = await session.execute(
            select(ClassSchedule).where(ClassSchedule.group_id == user.group_id)
        )
        classes = list(rows.scalars())

    days: list[DayOut] = []
    for offset in range(settings.horizon_days):
        d = today + timedelta(days=offset)
        wd = d.weekday()

        day_classes = sorted(
            (c for c in classes if c.weekday == wd),
            key=lambda c: to_min(c.start_time),
        )
        day_protected = sorted(
            (p for p in protected if p.weekday == wd),
            key=lambda p: to_min(p.start_time),
        )

        # «пара > защищённое окно > свободно»: защищённый час не считается
        # свободным временем (показывается отдельным слотом ниже).
        busy_for_free = [
            (to_min(c.start_time), to_min(c.end_time)) for c in day_classes
        ] + [
            (to_min(p.start_time), to_min(p.end_time)) for p in day_protected
        ]
        free = free_intervals(day_start, day_end, busy_for_free)

        days.append(
            DayOut(
                date=d.isoformat(),
                weekday=wd,
                weekday_name=WEEKDAY_FULL[wd],
                is_today=(offset == 0),
                free=[IntervalOut(start=to_hhmm(s), end=to_hhmm(e)) for s, e in free],
                busy=[
                    BusyOut(
                        start=to_hhmm(to_min(c.start_time)),
                        end=to_hhmm(to_min(c.end_time)),
                        title=c.title,
                        kind="class",
                    )
                    for c in day_classes
                ],
                protected=[
                    BusyOut(
                        start=to_hhmm(to_min(p.start_time)),
                        end=to_hhmm(to_min(p.end_time)),
                        title=p.title,
                        kind="protected",
                    )
                    for p in day_protected
                ],
            )
        )

    return WeekOut(
        day_start=to_hhmm(day_start),
        day_end=to_hhmm(day_end),
        has_group=user.group_id is not None,
        group_name=group_name,
        days=days,
    )


# ---------- F5: проверка пересечений мероприятия ----------
def _event_segments(
    starts_at: datetime, ends_at: datetime, max_days: int = 14
) -> list[tuple[int, int, int]]:
    """Разбить мероприятие на посуточные сегменты (weekday, start_min, end_min).

    Корректно учитывает события через полночь и многодневные.
    """
    start_date = starts_at.date()
    end_date = ends_at.date()
    if end_date < start_date:
        end_date = start_date
    if (end_date - start_date).days > max_days:  # защита от патологий
        end_date = start_date + timedelta(days=max_days)

    segments: list[tuple[int, int, int]] = []
    cur = start_date
    while cur <= end_date:
        seg_start = to_min(starts_at.time()) if cur == start_date else 0
        seg_end = to_min(ends_at.time()) if cur == end_date else 24 * 60
        if cur == start_date == end_date and seg_end <= seg_start:
            # одинаковый день и некорректные данные — даём минимум час
            seg_end = min(24 * 60, seg_start + 60)
        if seg_end > seg_start:
            segments.append((cur.weekday(), seg_start, seg_end))
        cur += timedelta(days=1)
    return segments


async def load_schedule_context(
    session: AsyncSession, user: User
) -> tuple[list[ClassSchedule], list[ProtectedWindow], bool]:
    """Загрузить пары группы и защищённые окна один раз — для батч-проверки ленты."""
    if not user.group_id:
        return [], [], False
    rows = await session.execute(
        select(ClassSchedule).where(ClassSchedule.group_id == user.group_id)
    )
    classes = list(rows.scalars())
    department_id = await _department_id_for(session, user)
    protected = await _load_protected(session, department_id)
    return classes, protected, True


def conflict_for(
    classes: list[ClassSchedule],
    protected: list[ProtectedWindow],
    has_group: bool,
    starts_at: datetime,
    ends_at: datetime,
) -> ConflictOut:
    """Чистая детекция пересечений по заранее загруженным спискам (без БД)."""
    if not has_group:
        return ConflictOut(
            level="unknown",
            message="Группа не указана — укажи её в профиле, чтобы проверять пересечения.",
        )
    segments = _event_segments(starts_at, ends_at)
    if not segments:
        return ConflictOut(level="free", message="Попадает в свободное окно.")

    class_hits = [
        (wd, c)
        for wd, s, e in segments
        for c in classes
        if c.weekday == wd and overlaps(s, e, to_min(c.start_time), to_min(c.end_time))
    ]
    if class_hits:
        details = [
            f"{WEEKDAY_SHORT[wd]} {to_hhmm(to_min(c.start_time))}–"
            f"{to_hhmm(to_min(c.end_time))}" + (f" · {c.title}" if c.title else "")
            for wd, c in class_hits
        ]
        hwd, first = class_hits[0]
        return ConflictOut(
            level="class",
            message=f"Пересекается с парой ({WEEKDAY_SHORT[hwd]} "
            f"{to_hhmm(to_min(first.start_time))})"
            + (f": {first.title}" if first.title else ""),
            details=details,
        )

    prot_hits = [
        (wd, p)
        for wd, s, e in segments
        for p in protected
        if p.weekday == wd and overlaps(s, e, to_min(p.start_time), to_min(p.end_time))
    ]
    if prot_hits:
        return ConflictOut(
            level="protected",
            message="Попадает в защищённый внеучебный час — «своё» время для внеучебки.",
            details=[
                f"{WEEKDAY_SHORT[wd]} {to_hhmm(to_min(p.start_time))}–"
                f"{to_hhmm(to_min(p.end_time))} · {p.title}"
                for wd, p in prot_hits
            ],
        )

    return ConflictOut(level="free", message="Попадает в свободное окно — пар нет.")


async def check_conflict(
    session: AsyncSession, user: User, starts_at: datetime, ends_at: datetime
) -> ConflictOut:
    classes, protected, has_group = await load_schedule_context(session, user)
    return conflict_for(classes, protected, has_group, starts_at, ends_at)
