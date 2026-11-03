# -*- coding: utf-8 -*-
"""Тесты автоматического добавления дочерних подразделений при назначении прав.

Проверяют:
  - get_all_child_department_ids рекурсивно возвращает parent + всех детей;
  - нет детей -> только [parent_id];
  - защита от циклических ссылок (максимальная глубина рекурсии);
  - expand_department_ids_with_children раскрывает список без дубликатов.

Тесты не требуют PostgreSQL — используется in-memory SQLite.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SQLite вместо PostgreSQL для тестов (engine создаётся при импорте app.database)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.department import Department
from app.api.departments import (
    MAX_DEPARTMENT_TREE_DEPTH,
    expand_department_ids_with_children,
    get_all_child_department_ids,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Department.__table__])
    Session = sessionmaker(bind=engine)
    return Session()


def _seed(db):
    """Иерархия из примера задачи:
    1 Участок формовки...
      2 Раскрой
      3 Каландрирование
        5 Вулканизация (внук)
      4 Формовка
        6 ЛКП (внук)
    7 Цех сборки (без детей)
    """
    depts = [
        Department(id=1, name="Участок формовки...", parent_id=None),
        Department(id=2, name="Раскрой", parent_id=1),
        Department(id=3, name="Каландрирование", parent_id=1),
        Department(id=4, name="Формовка", parent_id=1),
        Department(id=5, name="Вулканизация", parent_id=3),
        Department(id=6, name="ЛКП", parent_id=4),
        Department(id=7, name="Цех сборки", parent_id=None),
    ]
    db.add_all(depts)
    db.commit()


def test_recursive_children_including_parent():
    db = _make_session()
    _seed(db)
    ids = sorted(get_all_child_department_ids(db, 1))
    assert ids == [1, 2, 3, 4, 5, 6], ids
    db.close()


def test_no_children_returns_only_parent():
    db = _make_session()
    _seed(db)
    assert get_all_child_department_ids(db, 7) == [7]
    # несуществующий id — тоже только он сам
    assert get_all_child_department_ids(db, 999) == [999]
    db.close()


def test_expand_list_no_duplicates():
    db = _make_session()
    _seed(db)
    # Родитель + его же дочернее + пересечение со списком -> без дубликатов
    result = expand_department_ids_with_children(db, [1, 2, 7, 1])
    assert sorted(result) == [1, 2, 3, 4, 5, 6, 7]
    assert len(result) == len(set(result))
    # Пустой/None список
    assert expand_department_ids_with_children(db, []) == []
    assert expand_department_ids_with_children(db, None) is not None
    # Строковые id приводятся к int
    assert expand_department_ids_with_children(db, ["7"]) == [7]
    db.close()


def test_cycle_protection():
    """Циклическая ссылка parent_id не должна приводить к бесконечной рекурсии."""
    db = _make_session()
    db.add_all([
        Department(id=10, name="A", parent_id=11),
        Department(id=11, name="B", parent_id=10),
    ])
    db.commit()
    ids = get_all_child_department_ids(db, 10)
    # Рекурсия останавливается по максимальной глубине
    assert len(ids) <= MAX_DEPARTMENT_TREE_DEPTH * 2 + 2
    assert ids[0] == 10
    db.close()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\nВсе тесты ({len(fns)}) пройдены.")
