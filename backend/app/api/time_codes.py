import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.time_code import TimeCode
from app.models.user import User

router = APIRouter(prefix="/time-codes", tags=["TimeCodes"])


class TimeCodeBase(BaseModel):
    code: str
    name: str
    hours_day: float = 0.0
    hours_night: float = 0.0
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Код не может быть пустым")
        if len(v) > 10:
            raise ValueError("Код слишком длинный (макс. 10 символов)")
        # буквенно-цифровые коды, дефис/точка допускаются (напр. 8н, В, ДМ)
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9\.\-]+", v):
            raise ValueError("Код может содержать только буквы, цифры, точку и дефис")
        return v


class TimeCodeCreate(TimeCodeBase):
    pass


class TimeCodeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    hours_day: Optional[float] = None
    hours_night: Optional[float] = None
    is_active: Optional[bool] = None


class TimeCodeOut(TimeCodeBase):
    id: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TimeCodeOut])
def list_time_codes(include_inactive: bool = False, db: Session = Depends(get_db),
                    user: User = Depends(require_admin)):
    """Справочник «Коды часов» доступен только Администратору."""
    q = db.query(TimeCode)
    if not include_inactive:
        q = q.filter(TimeCode.is_active == True)  # noqa: E712
    return q.order_by(TimeCode.code).all()


@router.post("/", response_model=TimeCodeOut)
def create_time_code(payload: TimeCodeCreate, db: Session = Depends(get_db),
                     user: User = Depends(require_admin)):
    """Добавлять записи в справочник может только Администратор."""
    code = payload.code.strip()
    if db.query(TimeCode).filter(TimeCode.code == code).first():
        raise HTTPException(status_code=400, detail=f"Код «{code}» уже существует")
    obj = TimeCode(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{code_id}", response_model=TimeCodeOut)
def update_time_code(code_id: int, payload: TimeCodeUpdate, db: Session = Depends(get_db),
                     user: User = Depends(require_admin)):
    obj = db.query(TimeCode).filter(TimeCode.id == code_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Код не найден")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"]:
        data["code"] = data["code"].strip()
        if db.query(TimeCode).filter(TimeCode.code == data["code"], TimeCode.id != code_id).first():
            raise HTTPException(status_code=400, detail="Такой код уже существует")
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{code_id}")
def delete_time_code(code_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_admin)):
    obj = db.query(TimeCode).filter(TimeCode.id == code_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Код не найден")
    db.delete(obj)
    db.commit()
    return {"ok": True}
