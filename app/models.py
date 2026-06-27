"""Модель данных (упрощённо по разделу 7 ТЗ).

Соглашения:
- weekday: 0=Пн ... 6=Вс (как datetime.weekday()).
- Время пар/окон хранится как time (повторяется еженедельно).
- Время мероприятий — конкретный datetime (наивный, в кампусном поясе).
- created_at и пр. отметки времени — наивный UTC (аудит).
"""
from __future__ import annotations

from datetime import datetime, time, timezone

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ----- перечисления (как строковые константы — переносимо между SQLite/PG) -----
class Role:
    STUDENT = "student"
    ORGANIZER = "organizer"
    ADMIN = "admin"
    ALL = {STUDENT, ORGANIZER, ADMIN}


class EventStatus:
    DRAFT = "draft"
    MODERATION = "moderation"
    PUBLISHED = "published"


class RegStatus:
    REGISTERED = "registered"
    CANCELLED = "cancelled"


class TMModule:
    HORIZONS = "horizons"  # «Расписание на 3 горизонта»
    GOALS = "goals"        # «Учебные цели»


def _utcnow() -> datetime:
    # наивный UTC без устаревшего datetime.utcnow()
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ----- ассоциативные таблицы M2M -----
user_interests = Table(
    "user_interests",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

event_tags = Table(
    "event_tags",
    Base.metadata,
    Column("event_id", ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# ----- справочники -----
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    groups: Mapped[list["Group"]] = relationship(back_populates="department")
    curators: Mapped[list["Curator"]] = relationship(back_populates="department")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)        # «ЭМИТ-101»
    direction: Mapped[str | None] = mapped_column(String(255))        # направление
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))

    department: Mapped["Department | None"] = relationship(back_populates="groups")
    classes: Mapped[list["ClassSchedule"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)


class Curator(Base):
    __tablename__ = "curators"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    contact: Mapped[str] = mapped_column(String(255))  # @username / ссылка / телефон
    note: Mapped[str | None] = mapped_column(String(255))

    department: Mapped["Department | None"] = relationship(back_populates="curators")


# ----- пользователи -----
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=Role.STUDENT)

    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"))
    goal: Mapped[str | None] = mapped_column(Text)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    group: Mapped["Group | None"] = relationship()
    interests: Mapped[list["Tag"]] = relationship(secondary=user_interests)
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tm_progress: Mapped[list["TMProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_profile(self) -> bool:
        return self.consent_at is not None and self.group_id is not None


# ----- расписание -----
class ClassSchedule(Base):
    """Еженедельная пара группы (РасписаниеЗанятий)."""

    __tablename__ = "class_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Пн ... 6=Вс
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    title: Mapped[str | None] = mapped_column(String(255))  # предмет/пара

    group: Mapped["Group"] = relationship(back_populates="classes")


class ProtectedWindow(Base):
    """Защищённый «внеучебный час» (ЗащищённоеОкно).

    department_id = NULL → окно действует глобально для всех отделений.
    """

    __tablename__ = "protected_windows"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    title: Mapped[str] = mapped_column(String(255), default="Внеучебный час")


# ----- мероприятия -----
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    organizer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String(255))

    # блок ценности (F4)
    value_skill: Mapped[str | None] = mapped_column(String(255))      # какой навык
    value_points: Mapped[int] = mapped_column(Integer, default=0)     # баллы в рейтинг
    value_portfolio: Mapped[str | None] = mapped_column(String(255))  # что в портфолио

    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=EventStatus.PUBLISHED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    organizer: Mapped["User | None"] = relationship()
    tags: Mapped[list["Tag"]] = relationship(secondary=event_tags)
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default=RegStatus.REGISTERED)
    conflict_note: Mapped[str | None] = mapped_column(String(512))  # подсветка на момент записи
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="registrations")
    event: Mapped["Event"] = relationship(back_populates="registrations")


# ----- тайм-менеджмент -----
class TMCard(Base):
    __tablename__ = "tm_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(32))  # horizons / goals
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)        # короткое объяснение
    task: Mapped[str] = mapped_column(Text)           # мини-задание / вопрос-рефлексия
    order: Mapped[int] = mapped_column(Integer, default=0)


class TMProgress(Base):
    __tablename__ = "tm_progress"
    __table_args__ = (UniqueConstraint("user_id", "card_id", name="uq_user_card"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(ForeignKey("tm_cards.id", ondelete="CASCADE"))
    answer: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="tm_progress")
    card: Mapped["TMCard"] = relationship()
