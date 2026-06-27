"""Демо-наполнение для сессии с первокурсниками ЭМИТ.

Идемпотентно: если в БД уже есть отделения — ничего не делаем.
Профиль dev-студента НЕ заполняем — чтобы на демо показать онбординг (сценарий A).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import campus_now

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
    TMCard,
    TMModule,
    User,
)


def _next_dt(weekday: int, hour: int, minute: int, base: datetime | None = None) -> datetime:
    """Ближайшее будущее наступление дня недели (минимум +1 день)."""
    base = base or campus_now()
    days_ahead = (weekday - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    d = base + timedelta(days=days_ahead)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


async def seed_if_empty(session: AsyncSession) -> None:
    existing = await session.scalar(select(func.count()).select_from(Department))
    if existing:
        return

    # ----- отделения ЭМИТ и группы -----
    dep_names = ["ОБИ", "ОПИ", "ОНЭ", "ОЭ", "ОМЭС", "Школа IT менеджмента", "Онлайн-программы"]
    departments = {name: Department(name=name) for name in dep_names}
    session.add_all(departments.values())
    await session.flush()

    # отделение → (направление, [группы])
    group_plan = {
        "ОБИ": ("Бизнес-информатика", ["БИ-1", "БИ-2", "БИ-3"]),
        "ОПИ": ("Прикладная информатика", ["ПИ-1", "ПИ-2", "ПИ-3"]),
        "ОНЭ": ("Национальная экономика", ["НЭ-1", "НЭ-2"]),
        "ОЭ": ("Экономика", ["Э-1", "Э-2"]),
        "ОМЭС": ("Мировая экономика и международный бизнес", ["МЭ-1", "МЭ-2"]),
        "Школа IT менеджмента": ("IT-менеджмент", ["ИТМ-1", "ИТМ-2"]),
        "Онлайн-программы": ("Онлайн-обучение", ["ОНЛ-1", "ОНЛ-2"]),
    }
    groups = {}
    for dep_name, (direction, gnames) in group_plan.items():
        for gn in gnames:
            groups[gn] = Group(
                name=gn, direction=direction, department_id=departments[dep_name].id
            )
    session.add_all(groups.values())
    await session.flush()
    demo = groups["БИ-1"]  # демо-группа, к ней привязано расписание

    # ----- расписание демо-группы БИ-1 (0=Пн … 6=Вс) -----
    schedule = [
        (0, "09:00", "10:30", "Математический анализ"),
        (0, "10:40", "12:10", "История"),
        (1, "10:40", "12:10", "Экономическая теория"),
        (1, "12:40", "14:10", "Английский язык"),
        (2, "09:00", "10:30", "Программирование"),
        (3, "09:00", "10:30", "Базы данных"),
        (4, "10:40", "12:10", "Философия"),
    ]
    for wd, s, e, title in schedule:
        sh, sm = map(int, s.split(":"))
        eh, em = map(int, e.split(":"))
        session.add(
            ClassSchedule(
                group_id=demo.id,
                weekday=wd,
                start_time=time(sh, sm),
                end_time=time(eh, em),
                title=title,
            )
        )

    # ----- защищённый внеучебный час (глобально, среда 13:00–14:00) -----
    session.add(
        ProtectedWindow(
            department_id=None,
            weekday=2,
            start_time=time(13, 0),
            end_time=time(14, 0),
            title="Внеучебный час",
        )
    )

    # ----- теги / интересы -----
    tag_names = [
        "IT", "Бизнес", "Спорт", "Творчество", "Волонтёрство",
        "Наука", "Медиа", "Языки", "Карьера", "Soft skills",
    ]
    tags = {name: Tag(name=name) for name in tag_names}
    session.add_all(tags.values())
    await session.flush()

    # ----- организатор (для авторства мероприятий) -----
    organizer = User(
        tg_id=100050,
        full_name="Анна Кураторова",
        username="curator_anna",
        role=Role.ORGANIZER,
    )
    session.add(organizer)
    await session.flush()

    # ----- мероприятия (привязаны к дням недели для демонстрации пересечений) -----
    def ev(title, wd, sh, sm, eh, em, tag_keys, skill, points, portfolio,
           location, description, capacity=None):
        e = Event(
            title=title,
            description=description,
            organizer_id=organizer.id,
            starts_at=_next_dt(wd, sh, sm),
            ends_at=_next_dt(wd, eh, em),
            location=location,
            value_skill=skill,
            value_points=points,
            value_portfolio=portfolio,
            capacity=capacity,
            status=EventStatus.PUBLISHED,
        )
        e.tags = [tags[k] for k in tag_keys]
        return e

    events = [
        # СР 13:00 — попадает в защищённый внеучебный час (позитив)
        ev("Хакатон ЭМИТ: 24 часа", 2, 13, 0, 15, 0, ["IT", "Карьера"],
           "командная разработка продукта", 30, "проект-кейс в портфолио",
           "Корпус 1, ауд. 305",
           "Сутки на то, чтобы собрать прототип в команде и защитить его перед жюри.",
           capacity=40),
        # ВТ 10:40 — пересекается с парой «Экономическая теория» (конфликт)
        ev("Лекция: личные финансы студента", 1, 10, 40, 12, 10, ["Бизнес", "Soft skills"],
           "финансовая грамотность", 10, None,
           "Корпус 2, актовый зал",
           "Как вести бюджет, копить и не уходить в минус на первом курсе."),
        # СБ 12:00 — свободное окно
        ev("Турнир по волейболу", 5, 12, 0, 14, 0, ["Спорт"],
           "командная игра, выносливость", 15, "спортивные достижения",
           "Спортзал РАНХиГС",
           "Межгрупповой турнир. Приходи командой или найди команду на месте."),
        # ЧТ 16:00 — свободное окно
        ev("Медиа-мастерская: монтаж reels", 3, 16, 0, 18, 0, ["Медиа", "Творчество"],
           "видеомонтаж и сторителлинг", 20, "ролик в портфолио",
           "Медиацентр",
           "За два часа смонтируешь свой первый ролик и разберёшь приёмы вовлечения."),
        # ПН 18:00 — свободное окно
        ev("Школа волонтёра", 0, 18, 0, 19, 30, ["Волонтёрство"],
           "организация мероприятий", 10, "волонтёрская книжка",
           "Корпус 1, ауд. 110",
           "Вводное занятие волонтёрского центра: куда приложить силы и как это засчитывается."),
        # ПТ 15:00 — свободное окно
        ev("Научный семинар: AI в экономике", 4, 15, 0, 16, 30, ["Наука", "IT"],
           "исследовательское мышление", 25, "тезисы доклада",
           "Корпус 2, ауд. 401",
           "Разбираем, как методы ML применяют в экономических исследованиях."),
    ]
    session.add_all(events)

    # ----- кураторы (F7) -----
    session.add_all([
        Curator(full_name="Игорь Наставников", department_id=departments["ОБИ"].id,
                contact="@emit_curator", note="Куратор первого курса"),
        Curator(full_name="Мария Проводник", department_id=departments["ОПИ"].id,
                contact="@emit_mentor", note="Внеучебная деятельность"),
        Curator(full_name="Денис Орлов", department_id=departments["Школа IT менеджмента"].id,
                contact="@itm_curator", note="Куратор Школы IT менеджмента"),
    ])

    # ----- ТМ-карточки (F6) -----
    session.add_all([
        TMCard(
            module=TMModule.HORIZONS,
            title="Расписание на 3 горизонта",
            content=(
                "Планируй на трёх горизонтах сразу:\n"
                "• Неделя — пары и репетиции;\n"
                "• Месяц — контрольные, дедлайны, экзамены;\n"
                "• Год — крупные события, курсовые, диплом.\n"
                "Так нагрузка перестаёт быть сюрпризом."
            ),
            task="Выпиши по одному делу на каждый горизонт: что важное есть на этой неделе, в этом месяце и в этом году?",
            order=1,
        ),
        TMCard(
            module=TMModule.GOALS,
            title="Учебные цели",
            content=(
                "Если есть скидка или стипендия — твоя цель «высокий балл», и от неё "
                "зависит объём подготовки. Когда цель названа, проще решать, на что "
                "хватает времени, а на что нет."
            ),
            task="Сформулируй свою учебную цель на семестр одним предложением.",
            order=2,
        ),
    ])

    await session.commit()
