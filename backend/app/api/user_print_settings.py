from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_print_settings import UserPrintSettings
from app.schemas.user_print_settings import (
    UserPrintSettingsResponse,
    UserPrintSettingsUpdate,
)
from datetime import datetime

router = APIRouter(prefix="/api/user-print-settings", tags=["UserPrintSettings"])

# Все доступные итоговые колонки (должны совпадать с summaryColumns
# во фронтенде — frontend/src/utils/tabelCalculations.js)
ALL_COLUMNS = [
    'fact_days', 'total_hours', 'vacation', 'sick', 'admin_leave',
    'weekend_holiday', 'other_absence', 'overtime_days', 'overtime_total',
    'overtime_hours',
    'night_hours', 'kdu_work_days', 'kdu_weekend_days', 'tariff_hours'
]


@router.get("/", response_model=UserPrintSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить настройки печати текущего пользователя."""
    settings = db.query(UserPrintSettings).filter(
        UserPrintSettings.user_id == current_user.id
    ).first()

    if not settings:
        # Создать настройки по умолчанию (все колонки)
        settings = UserPrintSettings(
            user_id=current_user.id,
            selected_columns=ALL_COLUMNS
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/", response_model=UserPrintSettingsResponse)
def update_settings(
    payload: UserPrintSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить настройки печати текущего пользователя."""
    # Валидация: нельзя сохранить пустой список
    if not payload.selected_columns:
        raise HTTPException(status_code=400, detail="Выберите хотя бы одну колонку")

    # Валидация: только допустимые колонки
    for col in payload.selected_columns:
        if col not in ALL_COLUMNS:
            raise HTTPException(status_code=400, detail=f"Недопустимая колонка: {col}")

    settings = db.query(UserPrintSettings).filter(
        UserPrintSettings.user_id == current_user.id
    ).first()

    if not settings:
        settings = UserPrintSettings(
            user_id=current_user.id,
            selected_columns=payload.selected_columns
        )
        db.add(settings)
    else:
        settings.selected_columns = payload.selected_columns
        settings.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(settings)
    return settings
