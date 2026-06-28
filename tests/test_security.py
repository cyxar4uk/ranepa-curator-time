"""Проверка валидации Telegram initData (в т.ч. с полем signature)."""
import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.security import InitDataError, parse_and_validate

TOKEN = "123456:TESTTOKEN"


def _make_init_data(fields: dict) -> str:
    """Собрать корректно подписанную initData (как это делает Telegram)."""
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


def test_valid_init_data_with_signature_field():
    # ключевой кейс: поле signature ДОЛЖНО входить в подпись (баг bad signature)
    user = json.dumps({"id": 42, "first_name": "Ия", "username": "iam"})
    init = _make_init_data(
        {"query_id": "AAA", "user": user, "auth_date": "9999999999", "signature": "ed25519"}
    )
    tg = parse_and_validate(init, TOKEN, max_age_seconds=None)
    assert tg.tg_id == 42
    assert tg.username == "iam"


def test_valid_without_signature():
    user = json.dumps({"id": 7, "first_name": "Тест"})
    init = _make_init_data({"user": user, "auth_date": "9999999999"})
    tg = parse_and_validate(init, TOKEN, max_age_seconds=None)
    assert tg.tg_id == 7


def test_bad_signature_rejected():
    init = "user=%7B%22id%22%3A1%7D&auth_date=9999999999&hash=deadbeef"
    with pytest.raises(InitDataError):
        parse_and_validate(init, TOKEN, max_age_seconds=None)


def test_empty_rejected():
    with pytest.raises(InitDataError):
        parse_and_validate("", TOKEN)
