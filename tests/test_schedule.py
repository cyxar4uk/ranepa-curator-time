"""Юнит-тесты ключевой логики свободных часов и пересечений (F2/F5)."""
from datetime import datetime, time

from app.services.schedule import (
    _event_segments,
    free_intervals,
    overlaps,
    to_hhmm,
    to_min,
)


def test_to_min_and_hhmm():
    assert to_min(time(9, 0)) == 540
    assert to_hhmm(540) == "09:00"
    assert to_hhmm(13 * 60 + 5) == "13:05"


def test_free_intervals_basic():
    # день 08:00–21:00, две пары — между ними и после остаются окна
    free = free_intervals(480, 1260, [(540, 630), (640, 730)])
    assert free == [(480, 540), (630, 640), (730, 1260)]


def test_free_intervals_merges_overlap():
    # перекрывающиеся занятые интервалы сливаются
    free = free_intervals(480, 1260, [(540, 660), (600, 720)])
    assert free == [(480, 540), (720, 1260)]


def test_free_intervals_full_day_busy():
    assert free_intervals(480, 1260, [(400, 1300)]) == []


def test_free_intervals_no_busy():
    assert free_intervals(480, 1260, []) == [(480, 1260)]


def test_overlaps_boundary_touch_is_not_conflict():
    assert overlaps(600, 660, 660, 720) is False
    assert overlaps(600, 660, 540, 600) is False


def test_overlaps_true():
    assert overlaps(600, 660, 630, 700) is True
    assert overlaps(600, 720, 610, 650) is True


def test_event_segments_same_day():
    d1 = datetime(2026, 6, 29, 13, 0)
    d2 = datetime(2026, 6, 29, 15, 0)
    assert _event_segments(d1, d2) == [(d1.weekday(), 780, 900)]


def test_event_segments_cross_midnight():
    d1 = datetime(2026, 6, 29, 23, 0)
    d2 = datetime(2026, 6, 30, 1, 0)
    # два сегмента: остаток первого дня и начало второго
    assert _event_segments(d1, d2) == [
        (d1.weekday(), 1380, 1440),
        (d2.weekday(), 0, 60),
    ]


def test_event_segments_caps_pathological_duration():
    d1 = datetime(2026, 1, 1, 10, 0)
    d2 = datetime(2027, 1, 1, 10, 0)  # год — должно быть ограничено
    segs = _event_segments(d1, d2)
    assert len(segs) <= 15
