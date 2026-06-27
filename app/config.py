"""Конфигурация приложения (читается из окружения / .env).

Один источник правды и для API (FastAPI), и для бота (aiogram).
"""
from __future__ import annotations

from datetime import datetime, time
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Telegram ---
    bot_token: str = ""
    webapp_url: str = "http://localhost:8000"

    # --- DB ---
    database_url: str = "sqlite+aiosqlite:///./curator.db"

    # --- Доступ ---
    admin_tg_ids: str = ""  # "111,222" — comma-separated

    # --- Dev ---
    # Безопасно по умолчанию: в проде initData проверяется по подписи.
    # Для локальной отладки в браузере поставьте DEV_MODE=true.
    dev_mode: bool = False
    dev_tg_id: int = 100001

    # Требовать модерацию админом перед публикацией мероприятия (F8/F9).
    # По умолчанию выключено: организатор добавил → сразу в ленте (критерий приёмки).
    require_moderation: bool = False

    # --- Расчёт свободных часов ---
    day_start: str = "08:00"
    day_end: str = "21:00"
    timezone: str = "Europe/Moscow"
    horizon_days: int = 7

    # ----- производные значения -----
    @property
    def admin_ids(self) -> set[int]:
        out: set[int] = set()
        for part in self.admin_tg_ids.replace(";", ",").split(","):
            part = part.strip()
            if part:
                try:
                    out.add(int(part))
                except ValueError:
                    continue
        return out

    @property
    def day_start_time(self) -> time:
        return _parse_hhmm(self.day_start, time(8, 0))

    @property
    def day_end_time(self) -> time:
        return _parse_hhmm(self.day_end, time(21, 0))


def _parse_hhmm(value: str, default: time) -> time:
    try:
        h, m = value.strip().split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return default


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def campus_now() -> datetime:
    """Текущее наивное время в кампусном поясе (settings.timezone).

    Приводит «сегодня»/«сейчас» к поясу кампуса независимо от TZ процесса.
    """
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None)
    except Exception:  # noqa: BLE001 — нет базы зон / неизвестный пояс
        return datetime.now()
