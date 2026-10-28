from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator, model_validator
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
from app.models.department import Department
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


def _normalize_allowed_departments(raw, db: Session) -> str:
    """Приводит значение прав на подразделения к каноничному виду в БД.

    Допустимые форматы на вход: "" (пусто), "*" (все), JSON-список id [1,2].
    Сохраняется: "" | '"*"' | JSON-список существующих id.
    """
    import json

    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    if s == "*":
        return '"*"'
    try:
        ids = json.loads(s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Некорректный формат подразделений")
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="Некорректный формат подразделений")
    clean = []
    for x in ids:
        try:
            did = int(x)
        except (ValueError, TypeError):
            continue
        if did not in clean and db.get(Department, did) is not None:
            clean.append(did)
    return json.dumps(clean) if clean else ""


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    # ✅ НОВОЕ ПОЛЕ (этап 1): единая роль (пока не влияет на логику)
    role: str = 'user'

    @field_validator("role", mode="before")
    @classmethod
    def _role_default(cls, v):
        # Обратная совместимость: если в БД NULL — считаем 'user'
        return v if v else "user"

    # ✅ НОВЫЕ ПОЛЯ (этап 3): область видимости данных (пока не влияет на логику)
    data_scope: str = 'own'

    @field_validator("data_scope", mode="before")
    @classmethod
    def _data_scope_default(cls, v):
        # Обратная совместимость: если в БД NULL — считаем 'own'
        return v if v else "own"

    @model_validator(mode="before")
    @classmethod
    def _fill_adid_json_from_orm(cls, values):
        # В модели SQLAlchemy новое поле этапа 3 называется allowed_department_ids_json.
        # Pydantic с from_attributes читает атрибуты по именам полей схемы; имя
        # allowed_department_ids в ORM занято property (старые права из колонки
        # allowed_departments). Поэтому при чтении из ORM явно берём колонку
        # allowed_department_ids_json и кладём её в dict для валидации.
        if isinstance(values, dict):
            return values
        data = {}
        for k in ("id", "username", "full_name", "role", "data_scope",
                  "is_admin", "is_hr", "timesheet_inspector", "is_user", "is_report",
                  "is_documents_manager", "permissions", "allowed_departments"):
            data[k] = getattr(values, k)
        data["allowed_department_ids_json"] = getattr(values, "allowed_department_ids_json", None)
        return data

    # ✅ СТАРЫЕ ПОЛЯ (продолжают работать)
    is_admin: bool
    is_hr: bool
    timesheet_inspector: bool
    is_user: bool = True
    is_report: bool = False
    is_documents_manager: bool = False  # Документы и приказы
    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)
    allowed_departments: str = ""   # JSON-список id подразделений или "*" — все
    allowed_department_ids_json: Optional[List[int]] = None  # ✅ НОВОЕ ПОЛЕ (этап 3)

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
    # ✅ НОВОЕ ПОЛЕ (этап 1): единая роль (пока не влияет на логику)
    role: str = 'user'
    # ✅ НОВЫЕ ПОЛЯ (этап 3): область видимости данных (пока не влияет на логику)
    data_scope: str = 'own'
    allowed_department_ids: Optional[List[int]] = None
    # ✅ СТАРЫЕ ПОЛЯ (продолжают работать)
    is_admin: bool = False
    is_hr: bool = False
    timesheet_inspector: bool = False
    is_user: bool = True
    is_report: bool = False
    is_documents_manager: bool = False
    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)
    allowed_departments: str = ""


class UserUpdate(BaseModel):
    password: Optional[str] = None
    full_name: Optional[str] = None
    # ✅ НОВОЕ ПОЛЕ (этап 1): единая роль (пока не влияет на логику)
    role: Optional[str] = None
    # ✅ НОВЫЕ ПОЛЯ (этап 3): область видимости данных (пока не влияет на логику)
    data_scope: Optional[str] = None
    allowed_department_ids: Optional[List[int]] = None
    # ✅ СТАРЫЕ ПОЛЯ (продолжают работать)
    is_admin: Optional[bool] = None
    is_hr: Optional[bool] = None
    timesheet_inspector: Optional[bool] = None
    is_user: Optional[bool] = None
    is_report: Optional[bool] = None
    is_documents_manager: Optional[bool] = None
    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)
    allowed_departments: Optional[str] = None


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
        role=payload.role,  # ✅ НОВОЕ ПОЛЕ (этап 1)
        data_scope=payload.data_scope,  # ✅ НОВОЕ ПОЛЕ (этап 3)
        allowed_department_ids_json=payload.allowed_department_ids,  # ✅ НОВОЕ ПОЛЕ (этап 3)
        is_admin=payload.is_admin,
        is_hr=payload.is_hr,
        timesheet_inspector=payload.timesheet_inspector,
        is_user=payload.is_user,
        permissions=payload.permissions,  # ✅ Права доступа к вкладкам (null — все страницы)
        allowed_departments=_normalize_allowed_departments(payload.allowed_departments, db),
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
    # ✅ ЭТАП 3: allowed_department_ids (из схемы) сохраняем в колонку allowed_department_ids_json
    if "allowed_department_ids" in data:
        data["allowed_department_ids_json"] = data.pop("allowed_department_ids")
    if "allowed_departments" in data:
        data["allowed_departments"] = _normalize_allowed_departments(data["allowed_departments"], db)
    if "permissions" in data and data["permissions"] is not None and not isinstance(data["permissions"], list):
        raise HTTPException(status_code=400, detail="Недопустимый формат прав доступа")
    for k, v in data.items():
        setattr(target, k, v)
    db.commit()
    db.refresh(target)
    return target
