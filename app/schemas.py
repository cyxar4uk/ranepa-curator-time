"""Pydantic-схемы для API (вход/выход)."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.config import settings


def _to_naive_campus(v: datetime) -> datetime:
    """Привести datetime к наивному кампусному времени.

    Клиент может прислать ISO со смещением (`...+03:00`) — переводим в пояс
    кампуса и срезаем tzinfo, чтобы не было сравнения naive/aware и неверного
    расчёта пересечений. Наивные значения оставляем как есть.
    """
    if v.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo

            v = v.astimezone(ZoneInfo(settings.timezone)).replace(tzinfo=None)
        except Exception:  # noqa: BLE001
            v = v.replace(tzinfo=None)
    return v


CampusDateTime = Annotated[datetime, AfterValidator(_to_naive_campus)]


# ---------- справочники ----------
class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    direction: str | None = None
    department_id: int | None = None


class CuratorOut(BaseModel):
    id: int
    full_name: str
    department_id: int | None = None
    department_name: str | None = None
    contact: str
    note: str | None = None


# ---------- профиль (F1) ----------
class MeOut(BaseModel):
    tg_id: int
    full_name: str | None = None
    role: str
    group: GroupOut | None = None
    department: DepartmentOut | None = None
    interests: list[TagOut] = []
    goal: str | None = None
    has_consent: bool
    has_profile: bool


class ProfileUpdate(BaseModel):
    """Онбординг / редактирование профиля."""
    group_id: int | None = None
    interest_ids: list[int] | None = None
    goal: str | None = None
    consent: bool | None = None  # согласие на обработку ПД (F1)


# ---------- свободные часы (F2) ----------
class IntervalOut(BaseModel):
    start: str  # "HH:MM"
    end: str    # "HH:MM"


class BusyOut(BaseModel):
    start: str
    end: str
    title: str | None = None
    kind: str  # "class" | "protected"


class DayOut(BaseModel):
    date: str            # ISO "YYYY-MM-DD"
    weekday: int         # 0=Пн
    weekday_name: str
    is_today: bool = False
    free: list[IntervalOut] = []
    busy: list[BusyOut] = []
    protected: list[BusyOut] = []


class WeekOut(BaseModel):
    day_start: str
    day_end: str
    has_group: bool
    group_name: str | None = None
    days: list[DayOut] = []


# ---------- ценность + пересечения ----------
class ValueOut(BaseModel):
    skill: str | None = None
    points: int = 0
    portfolio: str | None = None


class ConflictOut(BaseModel):
    """Результат проверки пересечений (F5)."""
    level: str           # "class" | "protected" | "free" | "unknown"
    message: str         # человекочитаемая подсветка
    details: list[str] = []


# ---------- лента / карточки (F3, F4) ----------
class EventCardOut(BaseModel):
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime
    location: str | None = None
    tags: list[TagOut] = []
    value: ValueOut
    capacity: int | None = None
    registered_count: int = 0
    is_registered: bool = False
    status: str = "published"
    conflict: ConflictOut | None = None  # вписывается ли в окно (для бейджа в ленте)


class EventDetailOut(EventCardOut):
    description: str | None = None
    organizer_name: str | None = None
    conflict: ConflictOut | None = None     # предпросмотр пересечения для текущего студента
    my_conflict_note: str | None = None     # что было подсвечено при записи


class RegistrationResultOut(BaseModel):
    registration_id: int
    status: str
    conflict: ConflictOut


# ---------- тайм-менеджмент (F6) ----------
class TMCardOut(BaseModel):
    id: int
    module: str
    title: str
    content: str
    task: str
    order: int = 0
    completed: bool = False
    answer: str | None = None


class TMCompleteIn(BaseModel):
    answer: str | None = None


# ---------- организатор (F8) ----------
class EventCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    starts_at: CampusDateTime
    ends_at: CampusDateTime
    location: str | None = None
    tag_ids: list[int] = []
    value_skill: str | None = None
    value_points: int = 0
    value_portfolio: str | None = None
    capacity: int | None = None


class EventUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    starts_at: CampusDateTime | None = None
    ends_at: CampusDateTime | None = None
    location: str | None = None
    tag_ids: list[int] | None = None
    value_skill: str | None = None
    value_points: int | None = None
    value_portfolio: str | None = None
    capacity: int | None = None


# ---------- админ (F9) ----------
class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    direction: str | None = None
    department_id: int | None = None


class CuratorCreateIn(BaseModel):
    full_name: str
    department_id: int | None = None
    contact: str
    note: str | None = None


class ProtectedWindowIn(BaseModel):
    department_id: int | None = None
    weekday: int = Field(ge=0, le=6)
    start_time: str  # "HH:MM"
    end_time: str
    title: str = "Внеучебный час"


class ProtectedWindowOut(BaseModel):
    id: int
    department_id: int | None = None
    weekday: int
    start_time: str
    end_time: str
    title: str


class GrantRoleIn(BaseModel):
    tg_id: int = Field(gt=0)
    role: Literal["student", "organizer"]  # admin — только через ADMIN_TG_IDS


class ModerationIn(BaseModel):
    approve: bool


class ImportSummaryOut(BaseModel):
    created_groups: int = 0
    created_rows: int = 0
    skipped: int = 0
    errors: list[str] = []


class SimpleOk(BaseModel):
    ok: bool = True
    detail: str | None = None
