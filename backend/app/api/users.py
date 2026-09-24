from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import List

from app.core.security import hash_password, require_admin
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


class RoleFlags(BaseModel):
    is_admin: bool = False            # Администратор
    is_hr: bool = False               # Кадровик
    timesheet_inspector: bool = False # Инспектор табелей


class UserWithRoles(RoleFlags):
    id: int
    username: str
    full_name: str

    class Config:
        from_attributes = True


class UserCreateWithRoles(RoleFlags):
    username: str
    password: str
    full_name: str = ""

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Логин не может быть пустым")
        if len(v) < 2:
            raise ValueError("Логин слишком короткий (мин. 2 символа)")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        return v


@router.get("/with-roles", response_model=List[UserWithRoles])
def list_users_with_roles(db: Session = Depends(get_db),
                          user: User = Depends(require_admin)):
    """Справочник пользователей с ролями — только для Администратора."""
    return db.query(User).order_by(User.username).all()


@router.post("/with-roles", response_model=UserWithRoles)
def create_user_with_roles(payload: UserCreateWithRoles, db: Session = Depends(get_db),
                           user: User = Depends(require_admin)):
    """Добавление пользователя с ролями — только для Администратора."""
    username = payload.username.strip()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail=f"Логин «{username}» уже существует")
    obj = User(
        username=username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        is_admin=payload.is_admin,
        is_hr=payload.is_hr,
        timesheet_inspector=payload.timesheet_inspector,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/with-roles/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_admin)):
    """Удаление пользователя — только для Администратора (нельзя удалить себя)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    db.delete(target)
    db.commit()
    return {"ok": True}
