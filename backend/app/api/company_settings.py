from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.company_setting import CompanySetting
from app.models.user import User

router = APIRouter(prefix="/company-settings", tags=["CompanySettings"])

DEFAULT_POSITION = "Генеральный директор"


class CompanySettingsBase(BaseModel):
    company_name: str = ""
    director_position: str = DEFAULT_POSITION
    director_name: str = ""
    # Порог переработки в минутах (общий для всех графиков). 0 = считать любую переработку.
    overtime_threshold: int = 0

    @field_validator("company_name", "director_name", "director_position")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        v = (v or "").strip()
        return v

    @field_validator("overtime_threshold")
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        v = int(v or 0)
        if v < 0:
            raise ValueError("Порог переработки не может быть отрицательным")
        return v


class CompanySettingsUpdate(CompanySettingsBase):
    pass


class CompanySettingsOut(CompanySettingsBase):
    id: int

    class Config:
        from_attributes = True


def _get_or_create(db: Session) -> CompanySetting:
    settings = db.query(CompanySetting).order_by(CompanySetting.id).first()
    if settings is None:
        settings = CompanySetting(
            company_name="",
            director_position=DEFAULT_POSITION,
            director_name="",
            overtime_threshold=0,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_overtime_threshold(db: Session) -> int:
    """Общий порог переработки (минуты) из настроек системы.

    Используется при расчёте сверхурочных в фактическом табеле и отчётах.
    0 = считать любую переработку (старое поведение).
    """
    settings = db.query(CompanySetting).order_by(CompanySetting.id).first()
    return int(getattr(settings, "overtime_threshold", 0) or 0) if settings else 0


def apply_overtime_threshold(fact_hours: float, base_hours: float, threshold_minutes: int) -> float:
    """Сверхурочные с учётом порога: если переработка (в минутах) <= порога — 0.

    Порог 0 = старое поведение (считается любое превышение).
    """
    raw_ot_hours = (fact_hours or 0.0) - (base_hours or 0.0)
    if raw_ot_hours <= 0:
        return 0.0
    if threshold_minutes and round(raw_ot_hours * 60, 6) <= threshold_minutes:
        return 0.0
    return max(0.0, round(raw_ot_hours, 2))


@router.get("/", response_model=CompanySettingsOut)
def read_company_settings(db: Session = Depends(get_db),
                          user: User = Depends(get_current_user)):
    """Чтение настроек предприятия — всем авторизованным (нужно для отчётов/шапок)."""
    return _get_or_create(db)


@router.put("/", response_model=CompanySettingsOut)
def update_company_settings(payload: CompanySettingsUpdate,
                            db: Session = Depends(get_db),
                            user: User = Depends(require_admin)):
    """Сохранение настроек — только Администратор."""
    if not payload.company_name:
        raise HTTPException(status_code=400, detail="Название предприятия обязательно")
    if not payload.director_name:
        raise HTTPException(status_code=400, detail="ФИО руководителя обязательно")
    if not payload.director_position:
        payload.director_position = DEFAULT_POSITION

    settings = _get_or_create(db)
    settings.company_name = payload.company_name
    settings.director_position = payload.director_position
    settings.director_name = payload.director_name
    settings.overtime_threshold = payload.overtime_threshold
    db.commit()
    db.refresh(settings)
    return settings
