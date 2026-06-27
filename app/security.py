"""Валидация Telegram WebApp initData (раздел 6 ТЗ: идентификатор — Telegram ID).

Алгоритм (официальный):
  secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
  data_check_string = "\\n".join(sorted "key=value" по всем полям, кроме hash и signature)
  ожидаемый hash = HMAC_SHA256(key=secret_key, msg=data_check_string) в hex
Сверяем с полем hash из initData.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


@dataclass
class TgUser:
    tg_id: int
    full_name: str | None = None
    username: str | None = None


class InitDataError(Exception):
    pass


def _full_name(first: str | None, last: str | None) -> str | None:
    parts = [p for p in (first, last) if p]
    return " ".join(parts) if parts else None


def parse_and_validate(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int | None = 24 * 3600,
) -> TgUser:
    """Проверить подпись initData и вернуть пользователя Telegram."""
    if not init_data:
        raise InitDataError("empty init data")
    if not bot_token:
        raise InitDataError("bot token is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash is missing")
    # ВАЖНО: поле `signature` (Ed25519 для сторонней проверки) НЕ исключаем —
    # оно входит в data_check_string при расчёте HMAC `hash` (как в aiogram).

    data_check_string = "\n".join(
        f"{k}={pairs[k]}" for k in sorted(pairs.keys())
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("bad signature")

    # свежесть (защита от повторного использования старых initData)
    if max_age_seconds is not None:
        auth_date = pairs.get("auth_date")
        if auth_date and auth_date.isdigit():
            if time.time() - int(auth_date) > max_age_seconds:
                raise InitDataError("init data expired")

    user_raw = pairs.get("user")
    if not user_raw:
        raise InitDataError("user is missing")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("user is not valid json") from exc

    tg_id = user.get("id")
    if not isinstance(tg_id, int):
        raise InitDataError("user id is missing")

    return TgUser(
        tg_id=tg_id,
        full_name=_full_name(user.get("first_name"), user.get("last_name")),
        username=user.get("username"),
    )
