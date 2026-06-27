# Школа кураторов — Telegram Mini App + бот

[![CI](https://github.com/cyxar4uk/ranepa-curator-time/actions/workflows/ci.yml/badge.svg)](https://github.com/cyxar4uk/ranepa-curator-time/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**English summary.** "Curator School" is a Telegram Mini App plus bot (FastAPI, async SQLAlchemy,
aiogram 3, vanilla-JS frontend) that helps first-year students see their free hours, schedule
overlaps and the value of extracurricular events, so they can plan on their own after a single
session with a curator. It ships with demo data, Docker Compose (PostgreSQL) and a SQLite dev mode.
Documentation below is in Russian. MIT licensed.

> **Это неофициальный проект.** Он не является официальным продуктом РАНХиГС и не связан
> с Академией; названия отделений и демо-данные (кураторы, мероприятия, расписание) вымышлены
> и приведены только для демонстрации.

## Зачем

MVP по ТЗ «Школа кураторов». Реализует стратегию **«автономия за одну сессию»**:
бот — рычаг, который за одну сессию с куратором учит первокурсника ЭМИТ самому
видеть свои свободные часы, пересечения и ценность мероприятий — и дальше
выбирать без куратора.

## Что внутри (F1–F9 из ТЗ)

| ID | Функция | Где |
|----|---------|-----|
| F1 | Онбординг и профиль (отделение → группа → интересы → цель → **согласие на ПД**) | Mini App: онбординг |
| F2 | Свободные часы на скользящую неделю + защищённый внеучебный час | вкладка «Часы» |
| F3 | Лента мероприятий по интересам/тегам (переключатель «по интересам / все») | вкладка «Лента» |
| F4 | Карточки ценности (навык / баллы / портфолио) | карточка мероприятия |
| F5 | Запись + подсветка пересечений с парами и защищённым окном | карточка мероприятия |
| F6 | Тайм-менеджмент: «3 горизонта» и «Учебные цели» (с мини-заданием) | вкладка «ТМ» |
| F7 | Контакты кураторов отделения | вкладка «Кураторы» |
| F8 | Кабинет организатора (ввод/редактирование мероприятий, счётчик записей) | роль organizer/admin |
| F9 | Админка: загрузка расписания (CSV), теги/группы/кураторы, защищённое окно, модерация, выдача ролей | роль admin |

## Архитектура

```
Telegram ──▶ aiogram-бот (/start) ──▶ кнопка «Открыть приложение»
                                          │
                                          ▼
                              Telegram Mini App (frontend/, vanilla JS)
                                          │  fetch + initData
                                          ▼
                              FastAPI (app/) ──▶ PostgreSQL
```

- **Бэкенд:** FastAPI + async SQLAlchemy 2.0. Бизнес-логика в `app/services/`
  (расчёт свободных часов и детекция пересечений — `services/schedule.py`).
- **Авторизация:** Telegram WebApp `initData` (HMAC по токену бота), идентификатор —
  Telegram ID (раздел 6 ТЗ). Роли: `student` / `organizer` / `admin`.
- **Фронтенд:** статический Mini App без сборки (`frontend/`), отдаётся самим
  FastAPI. Стиль минимальный и семантичный — **дизайн накладывается позже**.
- **Бот:** `bot/` на aiogram 3.x — точка входа и запуск Mini App.

```
app/
  config.py        настройки (.env)
  db.py            async engine / сессии
  models.py        сущности (раздел 7 ТЗ)
  schemas.py       Pydantic-схемы API
  security.py      проверка Telegram initData
  deps.py          зависимости и ролевые гейты
  seed.py          демо-данные ЭМИТ
  services/        логика F1–F9
  routers/         HTTP-эндпоинты F1–F9
  main.py          сборка приложения + раздача Mini App
bot/main.py        aiogram-бот
frontend/          Mini App (index.html, js/, styles.css)
tests/             юнит- и интеграционные тесты
```

## Запуск через Docker (прод-подобно, PostgreSQL)

```bash
cp .env.example .env   # Windows: copy .env.example .env
# впишите BOT_TOKEN и WEBAPP_URL (HTTPS-адрес, где будет доступен Mini App)
docker compose up --build
```

Поднимутся три сервиса: `db` (Postgres), `app` (API + Mini App на :8000), `bot`.
Таблицы и демо-данные создаются автоматически при старте.

## Локальный запуск без Docker (SQLite)

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# API + Mini App (SQLite, dev-режим)
DEV_MODE=true DATABASE_URL="sqlite+aiosqlite:///./curator.db" \
  uvicorn app.main:app --reload --port 8000

# в отдельном терминале — бот (нужен BOT_TOKEN)
BOT_TOKEN="<токен>" python -m bot.main
```

Открыть в браузере: `http://localhost:8000` — в `DEV_MODE` приложение работает
без Telegram, входя под `DEV_TG_ID`.

### Отладка ролей в браузере

В `DEV_MODE` можно подменить пользователя query-параметром:

- студент: `http://localhost:8000/?dev_tg_id=100001`
- админ: добавьте id в `ADMIN_TG_IDS` (`.env`) и откройте `…/?dev_tg_id=<этот id>`
- организатор: войдите админом и выдайте роль на вкладке «Профиль организатора»,
  либо в админке → «Выдать доступ».

## Боевое подключение к Telegram

1. Создайте бота у **@BotFather**, получите `BOT_TOKEN`.
2. Разместите Mini App по HTTPS, укажите адрес в `WEBAPP_URL`
   (локально — туннель ngrok/cloudflared на `http://localhost:8000`).
3. `DEV_MODE=false` — тогда `initData` проверяется по подписи (без неё — 401).
4. `/start` в боте даст кнопку «Открыть приложение».

## Формат CSV расписания (F9)

Загрузка в админке → «Расписание групп (CSV)». UTF-8, разделитель `,` или `;`:

```csv
group,weekday,start,end,title
ЭМИТ-101,0,09:00,10:30,Математический анализ
ЭМИТ-101,2,09:00,10:30,Программирование
```

- `weekday`: `0`=Пн … `6`=Вс (также принимаются `пн/вт/…`).
- Повторная загрузка группы **полностью заменяет** её расписание (обновление).
- Неизвестные группы создаются автоматически.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `BOT_TOKEN` | токен бота (обязателен в проде — им проверяется `initData`) |
| `WEBAPP_URL` | HTTPS-адрес Mini App |
| `DATABASE_URL` | `postgresql+asyncpg://…` или `sqlite+aiosqlite:///…` |
| `ADMIN_TG_IDS` | Telegram ID администраторов (через запятую) |
| `DEV_MODE` | `true` — без проверки подписи (только разработка) |
| `DEV_TG_ID` | под кем входить в dev-режиме |
| `DAY_START`, `DAY_END` | границы «учебного дня» для расчёта свободных часов |
| `HORIZON_DAYS` | горизонт ленты/часов (дней) |
| `TIMEZONE` | часовой пояс кампуса (по умолчанию `Europe/Moscow`) |
| `REQUIRE_MODERATION` | требовать модерацию мероприятий перед публикацией |

## Тесты

```bash
pip install -r requirements.txt
pytest -q
```

Тесты используют локальный SQLite-файл `test_curator.db` (создаётся автоматически, в git не попадает).
CI (GitHub Actions) запускает `pytest` на каждый push и pull request. Сборки фронтенда нет —
Mini App статический.

- `tests/test_schedule.py` — расчёт свободных окон и детекция пересечений.
- `tests/test_api.py` — сквозной прогон по критериям приёмки MVP.

## Критерии приёмки MVP (раздел 9 ТЗ) — как закрыты

- ✅ Студент проходит онбординг, видит свободные часы по группе и защищённое окно.
- ✅ Лента фильтруется по интересам, на каждом — карточка ценности.
- ✅ При записи показывается пересечение с парами / защищённым окном.
- ✅ Студент проходит обе ТМ-карточки.
- ✅ Организатор добавляет мероприятие — оно появляется в ленте.
- ✅ Админ грузит расписание (CSV) и теги; доступны контакты кураторов.

## Дорожная карта (вне MVP, раздел 7 стратегии)

Персональный календарь с авто-учётом репетиций, трекинг участия, дашборд куратора,
полноценная прямая связь с куратором, интеграции (SSO, авто-импорт расписания).

## Открытые вопросы из ТЗ (раздел 10)

Подтвердить платформу; согласовать источник/формат расписания; согласование
обработки ПД со службой безопасности (152-ФЗ); кто организаторы и как получают
доступ; кто ведёт справочники; доверять ли самовводу группы.
```

## Безопасность

Не коммитьте `.env` и токен бота. `DEV_MODE=true` отключает проверку подписи `initData` —
используйте только локально. Пароль Postgres `curator` в `docker-compose.yml` — значение для
локальной разработки; смените его и не публикуйте порт `5432` в продакшене.

## Лицензия

[MIT](LICENSE) © 2026 Ilia Melnikov. Изменения по версиям — в [CHANGELOG.md](CHANGELOG.md).
