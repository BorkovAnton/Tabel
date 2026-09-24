from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base  # ← Теперь engine здесь есть!
from app.api import employees, turnstile, timesheet
from app.api.turnstile_fix import router as turnstile_fix_router
from app.api.departments import router as departments_router
from app.api.schedules import router as schedules_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tabel System", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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

@app.get("/health")
async def health_check():
    return {"status": "ok"}