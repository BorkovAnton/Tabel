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

    @field_validator("company_name", "director_name", "director_position")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        v = (v or "").strip()
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
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


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
    db.commit()
    db.refresh(settings)
    return settings
