"""Тесты парных смен с учётом обеденных перерывов (< 90 минут).

Проверяют исправление: «Выход -> Вход» короче LUNCH_BREAK_THRESHOLD_MINUTES —
обед, а не конец смены; такие события объединяются в одну смену.

Запуск из каталога backend/:  python tests/test_pair_shifts.py
(или python -m pytest tests/, если установлен pytest)
"""
import sys
import types
import importlib.util
from datetime import datetime


def _load_tf():
    """Загрузить turnstile_fix со заглушками внешних зависимостей
    (fastapi/sqlalchemy нужны только для роутера, не для логики пар)."""
    class DummyBase:
        pass

    class Dm:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, n):
            return self

        def __call__(self, *a, **k):
            return self

    dummy = Dm()
    attrs = dict(APIRouter=dummy, Depends=dummy, HTTPException=Exception, Query=dummy,
                 Session=object, BaseModel=DummyBase, func=dummy, get_db=dummy,
                 TurnstileEvent=DummyBase, Employee=DummyBase, Department=DummyBase,
                 TimesheetRecord=DummyBase)
    for mod in ["fastapi", "sqlalchemy", "sqlalchemy.orm", "pydantic",
                "app.database", "app.models", "app.models.turnstile_event",
                "app.models.employee", "app.models.department",
                "app.models.timesheet_record"]:
        m = types.ModuleType(mod)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[mod] = m

    here = __file__
    path = here[:here.index("tests")] + "app/api/turnstile_fix.py"
    spec = importlib.util.spec_from_file_location("tf_under_test", path)
    tf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tf)
    return tf


tf = _load_tf()


class Ev:
    def __init__(self, emp, dt, et, shift_end=None):
        self.employee_id = emp
        self.datetime = dt
        self.event_type = et
        self.shift_end = shift_end


def D(d, t):
    return datetime.fromisoformat(f"{d} {t}")


def test_lunch_break_merged_into_single_shift():
    """Пример из задачи: 08:17 in, 12:32 out, 12:54 in, 16:01 out —
    одна смена 08:17->16:01 (7ч44м), обед 22 минуты."""
    evs = [Ev(1, D("2026-10-30", "08:17"), "in"), Ev(1, D("2026-10-30", "12:32"), "out"),
           Ev(1, D("2026-10-30", "12:54"), "in"),  Ev(1, D("2026-10-30", "16:01"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1, f"ожидалась одна смена, получено {len(sh)}"
    s = sh[0]
    assert s["first_in"] == D("2026-10-30", "08:17")
    assert s["last_out"] == D("2026-10-30", "16:01")
    assert abs(s["duration_hours"] - 7.73) < 0.01          # 7ч44м
    assert s["lunch_break_minutes"] == 22                  # 12:32 -> 12:54
    assert s["lunch_breaks"][0]["start"] == D("2026-10-30", "12:32")
    # fact_hours при вычитании обеда: 7.73 - 22/60 ~ 7.36
    assert round(s["duration_hours"] - s["lunch_break_minutes"] / 60, 2) == 7.36


def test_long_break_is_two_shifts():
    """Перерыв >= 90 минут — это две отдельные смены, не обед."""
    evs = [Ev(1, D("2026-10-30", "08:00"), "in"), Ev(1, D("2026-10-30", "12:00"), "out"),
           Ev(1, D("2026-10-30", "14:00"), "in"),  Ev(1, D("2026-10-30", "18:00"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 2
    assert all(s["has_out"] for s in sh)
    assert all(s["lunch_break_minutes"] == 0 for s in sh)


def test_night_shift_across_midnight():
    """Ночная смена 22:47 -> 07:02 следующего дня остаётся одной сменой."""
    evs = [Ev(2, D("2026-10-29", "22:47"), "in"), Ev(2, D("2026-10-30", "07:02"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1 and sh[0]["is_night"]
    assert sh[0]["last_out"].date().isoformat() == "2026-10-30"


def test_night_shift_with_short_break():
    """Ночная смена с коротким перерывом после выхода до полудня —
    по-прежнему одна смена, перерыв учтён как обед."""
    evs = [Ev(2, D("2026-10-29", "22:47"), "in"), Ev(2, D("2026-10-30", "06:00"), "out"),
           Ev(2, D("2026-10-30", "06:20"), "in"),  Ev(2, D("2026-10-30", "07:02"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1 and sh[0]["is_night"]
    assert sh[0]["lunch_break_minutes"] == 20


def test_missing_out():
    evs = [Ev(3, D("2026-10-30", "09:00"), "in")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1 and not sh[0]["has_out"] and sh[0]["duration_hours"] is None


def test_missing_in():
    evs = [Ev(4, D("2026-10-30", "15:00"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1 and not sh[0]["has_in"]


def test_manual_shift_untouched():
    evs = [Ev(5, D("2026-10-30", "09:00"), "shift", shift_end=D("2026-10-30", "17:30"))]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1 and sh[0]["is_manual"]
    assert sh[0]["duration_hours"] == 8.5
    assert sh[0]["lunch_break_minutes"] == 0


def test_two_lunch_breaks_one_shift():
    """Два коротких перерыва за день — одна смена, суммарный обед 30+40=70 мин."""
    evs = [Ev(6, D("2026-10-30", "08:00"), "in"), Ev(6, D("2026-10-30", "12:00"), "out"),
           Ev(6, D("2026-10-30", "12:30"), "in"),  Ev(6, D("2026-10-30", "13:00"), "out"),
           Ev(6, D("2026-10-30", "13:40"), "in"),  Ev(6, D("2026-10-30", "17:00"), "out")]
    sh = tf._pair_shifts(evs)
    assert len(sh) == 1
    assert sh[0]["lunch_break_minutes"] == 70


def test_detect_lunch_break_minutes():
    evs = [Ev(1, D("2026-10-30", "08:17"), "in"), Ev(1, D("2026-10-30", "12:32"), "out"),
           Ev(1, D("2026-10-30", "12:54"), "in"),  Ev(1, D("2026-10-30", "16:01"), "out")]
    assert tf.detect_lunch_break_minutes(evs) == 22
    assert tf.detect_lunch_break_minutes(
        [Ev(1, D("2026-10-30", "08:00"), "in"), Ev(1, D("2026-10-30", "17:00"), "out")]) == 0


if __name__ == "__main__":
    fails = []
    g = dict(globals())
    for name, fn in sorted(g.items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                fails.append(name)
    print("\nALL TESTS PASSED" if not fails else f"FAILURES: {fails}")
    sys.exit(1 if fails else 0)
