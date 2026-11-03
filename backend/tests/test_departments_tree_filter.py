# -*- coding: utf-8 -*-
"""Тесты фильтрации списка подразделений по правам (GET /departments/).

Проверяют исправление бага: пользователь с правами только на дочернее
подразделение (allowed=[45], parent_id=11) получал пустой список, потому что
build_tree начинает обход от корневых узлов и не находил корень 11.

Тесты:
  - add_ancestors_for_tree догружает цепочку предков, помечая их is_service;
  - дерево связно: разрешённый дочерний узел виден под служебным родителем;
  - flat-режим возвращает только разрешённые подразделения (is_service=False);
  - флаг all=True игнорируется для не-администратора (защита роли admin);
  - администратор с all=True получает полный список.

SQLite in-memory, без PostgreSQL.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Полный импорт моделей: иначе позже подгружаемый app.models.employee не даёт
# SQLAlchemy разрешить строковые relationship() в реестре классов (flaky fail).
import app.models  # noqa: F401

from app.database import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.api.departments import (
    DepartmentResponse,
    add_ancestors_for_tree,
    build_tree,
    get_departments,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[Department.__table__,
                                                  Employee.__table__])
    Session = sessionmaker(bind=engine)
    return Session()


def _seed(db):
    """Иерархия из задачи: 11 — родитель, 45 — дочернее «Раскрой», 50 — внук."""
    depts = [
        Department(id=1, name="Завод", parent_id=None),
        Department(id=11, name="Участок формовки...", parent_id=1),
        Department(id=45, name="Раскрой", parent_id=11),
        Department(id=46, name="Каландрирование", parent_id=11),
        Department(id=50, name="Подучасток раскроя", parent_id=45),
        Department(id=99, name="Цех сборки", parent_id=None),
    ]
    db.add_all(depts)
    db.commit()


def _collect_ids(nodes):
    ids = []
    for n in nodes:
        ids.append(n["id"])
        ids.extend(_collect_ids(n.get("children") or []))
    return ids


def test_add_ancestors_loads_parent_chain():
    db = _make_session()
    _seed(db)
    allowed = db.query(Department).filter(Department.id.in_([45])).all()
    extended, service_ids = add_ancestors_for_tree(db, allowed)

    ids = {d.id for d in extended}
    assert 45 in ids and 11 in ids and 1 in ids, ids
    # служебные предки помечены
    assert service_ids == {11, 1}
    by = {d.id: d for d in extended}
    assert getattr(by[45], "is_service", False) in (None, False)
    assert by[11].is_service is True and by[1].is_service is True
    db.close()


def test_tree_is_connected_for_child_only_permissions():
    db = _make_session()
    _seed(db)
    allowed = db.query(Department).filter(Department.id.in_([45])).all()
    departments, _ = add_ancestors_for_tree(db, allowed)
    tree = build_tree(departments, None, db)

    ids = _collect_ids(tree)
    # дерево непустое и содержит разрешённое дочернее подразделение
    assert 45 in ids, ids
    # предки присутствуют для связности
    assert 11 in ids and 1 in ids

    def find(nodes, dept_id):
        for n in nodes:
            if n["id"] == dept_id:
                return n
            got = find(n["children"], dept_id)
            if got:
                return got
        return None

    assert find(tree, 45)["is_service"] is False
    assert find(tree, 11)["is_service"] is True
    assert find(tree, 1)["is_service"] is True
    db.close()


def _make_user(role, data_scope, allowed_json):
    u = User(username=f"u_{role}_{data_scope}", role=role,
             data_scope=data_scope,
             allowed_department_ids_json=allowed_json)
    return u


def test_endpoint_returns_visible_list_for_manager_with_child_only_rights():
    """Репродукция бага: manager, custom, allowed=[45] -> список не пуст."""
    db = _make_session()
    _seed(db)
    user = _make_user("manager", "custom", [45])

    result = get_departments(flat=False, all=False, db=db, user=user)
    ids = _collect_ids(result)
    assert 45 in ids, f"пустое/неполное дерево: {ids}"
    assert 99 not in ids  # чужое подразделение не видно

    # плоский режим: только разрешённые, служебные предки помечены
    flat = get_departments(flat=True, all=False, db=db, user=user)
    flat_models = [DepartmentResponse(**row) for row in flat]
    # allowed_department_id_set раскрывает дочерние -> видимы 45 и внук 50
    selectable = {d.id for d in flat_models if not d.is_service}
    assert selectable == {45, 50}, selectable
    parents = {d.id for d in flat_models if d.is_service}
    assert parents == {11, 1}, parents
    db.close()


def test_all_flag_protected_for_non_admin():
    db = _make_session()
    _seed(db)
    user = _make_user("manager", "custom", [45])

    # не-админ с all=True не должен получить полный список
    result = get_departments(flat=True, all=True, db=db, user=user)
    models = [DepartmentResponse(**row) for row in result]
    selectable = {d.id for d in models if not d.is_service}
    assert selectable == {45, 50}, selectable
    assert 99 not in {d.id for d in models}
    assert 46 not in {d.id for d in models}
    db.close()


def test_all_flag_works_for_admin():
    db = _make_session()
    _seed(db)
    admin = _make_user("admin", "all", [])

    result = get_departments(flat=True, all=True, db=db, user=admin)
    models = [DepartmentResponse(**row) for row in result]
    ids = {d.id for d in models}
    assert ids == {1, 11, 45, 46, 50, 99}, ids
    assert all(not d.is_service for d in models)
    db.close()


def test_root_permission_sees_children_in_tree():
    """Права на корневое 11 (родитель) -> в дереве видны он и все дочерние."""
    db = _make_session()
    _seed(db)
    user = _make_user("manager", "custom", [11])

    result = get_departments(flat=False, all=False, db=db, user=user)
    ids = set(_collect_ids(result))
    assert {11, 45, 46, 50} <= ids, ids
    assert 99 not in ids
    db.close()
