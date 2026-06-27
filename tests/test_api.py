"""Интеграционный smoke-тест: проходит по критериям приёмки MVP (раздел 9 ТЗ)."""
import pytest

STUDENT = {}  # dev_tg_id=100001 по умолчанию
ADMIN = {"X-Dev-Tg-Id": "999001"}  # есть в ADMIN_TG_IDS


async def _find_event(client, title_part):
    r = await client.get("/api/events", params={"by_interests": "false"})
    assert r.status_code == 200
    for ev in r.json():
        if title_part.lower() in ev["title"].lower():
            return ev
    raise AssertionError(f"событие '{title_part}' не найдено")


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_full_student_flow(client):
    # --- онбординг: профиль пуст ---
    me = (await client.get("/api/me")).json()
    assert me["role"] == "student"
    assert me["has_profile"] is False

    groups = (await client.get("/api/refs/groups")).json()
    g101 = next(g for g in groups if g["name"] == "БИ-1")
    tags = (await client.get("/api/refs/tags")).json()
    it_tag = next(t for t in tags if t["name"] == "IT")

    # сохранение профиля + согласие
    me = (
        await client.put(
            "/api/profile",
            json={"group_id": g101["id"], "interest_ids": [it_tag["id"]], "consent": True},
        )
    ).json()
    assert me["has_profile"] is True
    assert me["has_consent"] is True
    assert me["group"]["name"] == "БИ-1"

    # --- F2: свободные часы по группе + защищённое окно ---
    week = (await client.get("/api/schedule/week")).json()
    assert week["has_group"] is True
    assert len(week["days"]) == 7
    # хотя бы где-то есть защищённое окно и свободные интервалы
    assert any(d["protected"] for d in week["days"])
    assert any(d["free"] for d in week["days"])
    # в день с парами есть и занятые, и свободные слоты
    assert any(d["busy"] and d["free"] for d in week["days"])

    # --- F3/F4: лента по интересам, у каждого есть карточка ценности ---
    feed = (await client.get("/api/events", params={"by_interests": "true"})).json()
    assert len(feed) >= 1
    titles = {e["title"] for e in feed}
    assert any("Хакатон" in t for t in titles)  # IT-тег
    for e in feed:
        assert "value" in e

    # --- F5: пересечения ---
    hack = await _find_event(client, "Хакатон")  # СР 13:00 → защищённое окно
    detail = (await client.get(f"/api/events/{hack['id']}")).json()
    assert detail["conflict"]["level"] == "protected"

    lecture = await _find_event(client, "личные финансы")  # ВТ 10:40 → пара
    detail2 = (await client.get(f"/api/events/{lecture['id']}")).json()
    assert detail2["conflict"]["level"] == "class"

    # запись фиксирует подсветку
    reg = (await client.post(f"/api/events/{hack['id']}/register")).json()
    assert reg["status"] == "registered"
    assert reg["conflict"]["level"] == "protected"

    after = (await client.get(f"/api/events/{hack['id']}")).json()
    assert after["is_registered"] is True
    assert after["registered_count"] == 1

    # --- F6: ТМ-карточки ---
    cards = (await client.get("/api/tm")).json()
    assert len(cards) == 2
    done = (await client.post(f"/api/tm/{cards[0]['id']}/complete", json={"answer": "ок"})).json()
    assert done["completed"] is True

    # --- F7: кураторы ---
    curators = (await client.get("/api/curators")).json()
    assert len(curators) >= 1


async def test_student_cannot_access_admin(client):
    r = await client.get("/api/admin/protected-windows", headers=STUDENT)
    assert r.status_code == 403


async def test_admin_flow(client):
    # защищённые окна доступны админу
    r = await client.get("/api/admin/protected-windows", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()) >= 1

    me = (await client.get("/api/me", headers=ADMIN)).json()
    assert me["role"] == "admin"

    # F9: добавить тег
    r = await client.post("/api/admin/tags", json={"name": "Предпринимательство"}, headers=ADMIN)
    assert r.status_code == 200

    # F9: импорт расписания из CSV
    csv = "group,weekday,start,end,title\nЭМИТ-104,0,09:00,10:30,Введение\nЭМИТ-104,2,13:00,14:30,Семинар\n"
    files = {"file": ("schedule.csv", csv.encode("utf-8"), "text/csv")}
    r = await client.post("/api/admin/schedule/import", files=files, headers=ADMIN)
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["created_rows"] == 2
    assert summary["created_groups"] == 1


async def test_register_requires_consent(client):
    # новый пользователь без согласия не может записаться (152-ФЗ)
    new_user = {"X-Dev-Tg-Id": "100777"}
    me = (await client.get("/api/me", headers=new_user)).json()
    assert me["has_consent"] is False
    ev = (await client.get("/api/events", params={"by_interests": "false"}, headers=new_user)).json()[0]
    r = await client.post(f"/api/events/{ev['id']}/register", headers=new_user)
    assert r.status_code == 403


async def test_protected_hour_not_counted_as_free(client):
    # защищённый час (СР 13:00–14:00) не должен попадать в «свободно»
    groups = (await client.get("/api/refs/groups")).json()
    g101 = next(g for g in groups if g["name"] == "БИ-1")
    await client.put("/api/profile", json={"group_id": g101["id"], "consent": True})
    week = (await client.get("/api/schedule/week")).json()
    wed = next((d for d in week["days"] if d["weekday"] == 2), None)
    assert wed is not None
    assert any(p["start"] == "13:00" for p in wed["protected"])
    covers = lambda iv, t: iv["start"] <= t < iv["end"]  # noqa: E731
    assert not any(covers(f, "13:00") for f in wed["free"])


async def test_update_event_with_tags(client):
    # PUT с tag_ids на загруженном Event не должен падать (async lazy-load)
    tags = (await client.get("/api/refs/tags", headers=ADMIN)).json()
    payload = {
        "title": "Редактируемое",
        "starts_at": "2099-10-01T18:00:00",
        "ends_at": "2099-10-01T20:00:00",
        "tag_ids": [tags[0]["id"]],
    }
    created = (await client.post("/api/organizer/events", json=payload, headers=ADMIN)).json()
    r = await client.put(
        f"/api/organizer/events/{created['id']}",
        json={"title": "Изменено", "tag_ids": [tags[1]["id"]]},
        headers=ADMIN,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["title"] == "Изменено"
    assert {t["id"] for t in updated["tags"]} == {tags[1]["id"]}


async def test_event_accepts_aware_datetime(client):
    # ISO со смещением не должен ломать ленту (сравнение naive/aware)
    payload = {
        "title": "Событие с поясом",
        "starts_at": "2099-11-01T18:00:00+05:00",
        "ends_at": "2099-11-01T20:00:00+05:00",
        "tag_ids": [],
    }
    r = await client.post("/api/organizer/events", json=payload, headers=ADMIN)
    assert r.status_code == 200, r.text
    # лента строится и не падает на сравнении дат
    feed = await client.get("/api/events", params={"by_interests": "false"})
    assert feed.status_code == 200


async def test_grant_role_rejects_admin(client):
    r = await client.post("/api/admin/grant-role", json={"tg_id": 555001, "role": "admin"}, headers=ADMIN)
    assert r.status_code == 422  # Literal не пропускает 'admin'
    r2 = await client.post("/api/admin/grant-role", json={"tg_id": 555001, "role": "organizer"}, headers=ADMIN)
    assert r2.status_code == 200


async def test_organizer_create_event_appears_in_feed(client):
    # админ имеет права организатора → создаёт мероприятие
    tags = (await client.get("/api/refs/tags", headers=ADMIN)).json()
    payload = {
        "title": "Тестовый митап",
        "description": "проверка",
        "starts_at": "2099-09-01T18:00:00",
        "ends_at": "2099-09-01T20:00:00",
        "location": "ауд. 1",
        "tag_ids": [tags[0]["id"]],
        "value_skill": "нетворкинг",
        "value_points": 5,
        "value_portfolio": None,
        "capacity": 10,
    }
    r = await client.post("/api/organizer/events", json=payload, headers=ADMIN)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["status"] == "published"

    # появилось в общей ленте
    feed = (await client.get("/api/events", params={"by_interests": "false"})).json()
    assert any(e["title"] == "Тестовый митап" for e in feed)
