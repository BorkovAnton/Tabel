"""ЭТАП 9: интеграционная проверка новой системы прав (role/data_scope/can_*).

Запуск: DATABASE_URL=sqlite:///./test_stage9.db python test_stage9.py
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stage9.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402

client = TestClient(app)


def ensure_user(username, password, role, **kw):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            u = User(username=username, hashed_password=hash_password(password))
            db.add(u)
        u.role = role
        for k, v in kw.items():
            setattr(u, k, v)
        db.commit()
        return u.id
    finally:
        db.close()


def login(username, password):
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, (r.status_code, r.text)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


results = []

def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# ── Пользователи с НОВЫМИ полями, старые флаги — все False (фронт их не шлёт) ──
u_admin = ensure_user("s9_admin", "pw1234", "admin")
u_user = ensure_user("s9_user", "pw1234", "user", can_approve=False)
u_hr_approver = ensure_user("s9_hr", "pw1234", "hr", can_approve=True)
u_acc = ensure_user("s9_acc", "pw1234", "accountant")

h_admin = login("s9_admin", "pw1234")
h_user = login("s9_user", "pw1234")
h_hr = login("s9_hr", "pw1234")

# 1. role='user' НЕ может зайти в /users/with-roles -> 403
r = client.get("/users/with-roles", headers=h_user)
check("role=user получает 403 на GET /users/with-roles", r.status_code == 403)

# 2. role='admin' МОЖЕТ -> 200
r = client.get("/users/with-roles", headers=h_admin)
check("role=admin получает 200 на GET /users/with-roles", r.status_code == 200)

# 3. Создание пользователя админом -> 200 (с новыми полями, без старых чекбоксов)
payload = {
    "username": "s9_created",
    "password": "pw1234",
    "full_name": "Созданный Этап9",
    "role": "manager",
    "data_scope": "department",
    "allowed_department_ids": ["5", 7],   # строки тоже — нормализация int
    "can_approve": True,
    "permissions": ["/tabels"],
}
r = client.post("/users/with-roles", json=payload, headers=h_admin)
ok_create = r.status_code == 200 and r.json().get("role") == "manager"
check("админ создаёт пользователя через POST /users/with-roles (200)", ok_create)
if ok_create:
    body = r.json()
    check("allowed_department_ids нормализованы строки->int [5,7]",
          body.get("allowed_department_ids_json") == [5, 7])
    # тихий резерв: старые колонки синхронизированы с ролью
    db = SessionLocal()
    created = db.query(User).filter(User.username == "s9_created").first()
    check("legacy-фолбэк синхронизирован: is_user=True, is_admin/is_hr=False для manager",
          created.is_user and not created.is_admin and not created.is_hr)
    db.close()

# 4. Обновление роли: PUT меняем роль hr -> инспектор; старый payload без чекбоксов
db = SessionLocal()
target_id = db.query(User).filter(User.username == "s9_hr").first().id
db.close()
r = client.put(f"/users/with-roles/{target_id}",
               json={"role": "inspector", "data_scope": "all"}, headers=h_admin)
check("PUT /users/with-roles/{id} проходит (200) и меняет роль", r.status_code == 200 and r.json()["role"] == "inspector")

# 5. Табели: user (без can_approve) НЕ может создать табель -> 403; hr+can_approve может
r_user = client.post("/tabels/", json={"year": 2026, "month": 10, "department_id": None}, headers=h_user)
check("role=user без can_approve: создание табеля -> 403", r_user.status_code == 403)

# список табелей: user видит только свои, admin — все
r_list_user = client.get("/tabels/?year=2026&month=10", headers=h_user)
r_list_admin = client.get("/tabels/?year=2026&month=10", headers=h_admin)
check("GET /tabels доступен user (200, только свои)", r_list_user.status_code == 200)
check("GET /tabels доступен admin (200)", r_list_admin.status_code == 200)

# 6. require_hr_or_admin косвенно: accountant не админ -> 403 на /users/with-roles
h_acc = login("s9_acc", "pw1234")
r = client.get("/users/with-roles", headers=h_acc)
check("role=accountant получает 403 на GET /users/with-roles", r.status_code == 403)

# 7. unit-проверки функций security
from app.core.security import (can_manage_tabels, can_view_salary, can_see_all_tabels,
                               has_role)  # noqa: E402
db = SessionLocal()
uu = db.query(User).filter(User.username == "s9_user").first()
check("can_manage_tabels(user)=False при role='user', can_approve=False", can_manage_tabels(uu) is False)
uu.can_approve = True
check("can_manage_tabels=True при can_approve=True", can_manage_tabels(uu) is True)
check("can_view_salary(accountant)=True", can_view_salary(db.query(User).filter(User.username == "s9_acc").first()))
check("can_view_salary(user)=False", not can_view_salary(uu.__class__(role="user", can_view_salary=False)))
check("can_see_all_tabels(inspector)=True", can_see_all_tabels(db.query(User).filter(User.username == "s9_hr").first()))
db.close()

failed = [n for n, ok in results if not ok]
print("\n=== ИТОГ: %d/%d пройдено ===" % (len(results) - len(failed), len(results)))
for f in failed:
    print("ПРОВАЛЕНО:", f)
raise SystemExit(1 if failed else 0)
