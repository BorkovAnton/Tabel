from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    can_manage_tabels,
)
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    is_admin: bool
    is_hr: bool
    timesheet_inspector: bool
    is_user: bool = True

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str = ""
    is_admin: bool = False
    is_hr: bool = False
    timesheet_inspector: bool = False
    is_user: bool = True


class UserUpdate(BaseModel):
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_hr: Optional[bool] = None
    timesheet_inspector: Optional[bool] = None
    is_user: Optional[bool] = None


@router.post("/login", response_model=LoginResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_access_token({"sub": user.username})
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=List[UserOut])
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Список пользователей (для назначения ответственного за табель)."""
    if not can_manage_tabels(user):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return db.query(User).order_by(User.username).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администратор")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Логин уже существует")
    new_user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        is_admin=payload.is_admin,
        is_hr=payload.is_hr,
        timesheet_inspector=payload.timesheet_inspector,
        is_user=payload.is_user,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администратор")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        target.hashed_password = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    for k, v in data.items():
        setattr(target, k, v)
    db.commit()
    db.refresh(target)
    return target
