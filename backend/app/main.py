from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys as _sys
import os as _os
from app.database import engine, Base  # ← Теперь engine здесь есть!
from app.api import employees, turnstile, timesheet
from app.api.turnstile_fix import router as turnstile_fix_router
from app.api.departments import router as departments_router
from app.api.schedules import router as schedules_router
from app.api.auth import router as auth_router
from app.api.time_codes import router as time_codes_router
from app.api.users import router as users_router
from app.api.tabels import router as tabels_router
from app.api.holidays import router as holidays_router
from app.api.reports import router as reports_router
from app.api.company_settings import router as company_settings_router
from app.api.documents import router as documents_router
from app.api.dismissal_notes import router as dismissal_notes_router
from app.api.user_print_settings import router as user_print_settings_router
from app.api.import_positions import router as import_positions_router
from app.init_data import seed
from app.init_db import ensure_columns

# ✅ ПРОВЕРКА ВЕРСИИ КОДА (диагностика: контейнер использует актуальный код?)
print("=" * 60)
print("BACKEND STARTING")
print("=" * 60)
print(f"Python version: {_sys.version}")
try:
    import fastapi as _fastapi
    print(f"FastAPI version: {_fastapi.__version__}")
except Exception as _e:  # pragma: no cover
    print(f"FastAPI version: НЕ ОПРЕДЕЛЕНА ({_e})")
import app.main as _self_mod
print(f"main.py location: {_self_mod.__file__}")
_mpy = _os.path.join(_os.path.dirname(_self_mod.__file__), "init_db.py")
try:
    import hashlib as _hashlib
    with open(_mpy, "rb") as _f:
        _digest = _hashlib.sha256(_f.read()).hexdigest()[:12]
    print(f"init_db.py sha256: {_digest} (если хэш меняется после git pull — код в контейнере актуален)")
except Exception as _e:  # pragma: no cover
    print(f"init_db.py hash: не удалось вычислить ({_e})")
print("=" * 60)

# Авто-миграция: добавляем недостающие колонки в старые базы (до create_all)
print("[main] Вызываем ensure_columns()...")
ensure_columns()
print("[main] ensure_columns() завершена")

print("[main] Вызываем Base.metadata.create_all()...")
Base.metadata.create_all(bind=engine)
print("[main] Base.metadata.create_all() завершена")

# Инициализация справочников и пользователей по умолчанию
from app.database import SessionLocal
_db = SessionLocal()
try:
    seed(_db)
finally:
    _db.close()

app = FastAPI(title="Tabel System", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.100.61:3000",  # <-- ДОБАВИТЬ ВАШ IP
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрируем роутеры
app.include_router(employees.router)
app.include_router(turnstile.router)
app.include_router(timesheet.router)
app.include_router(turnstile_fix_router)
app.include_router(departments_router)
app.include_router(schedules_router)
app.include_router(auth_router)
app.include_router(time_codes_router)
app.include_router(users_router)
app.include_router(tabels_router)
app.include_router(holidays_router)
app.include_router(reports_router)
app.include_router(company_settings_router)
app.include_router(documents_router)
app.include_router(dismissal_notes_router)
app.include_router(user_print_settings_router)
app.include_router(import_positions_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}