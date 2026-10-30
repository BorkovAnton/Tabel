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
    is_admin_user,
)
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


def _normalize_dept_ids(raw) -> list[int]:
    """✅ ЭТАП 10: нормализация списка id подразделений в новую JSON-колонку.

    Принимает список id (числа или строки), "*" (все) или пустое значение;
    возвращает список int либо [] ('*' трактуется как data_scope='all',
    полный доступ задаётся через role/data_scope, а не через этот список).
    """
    if raw is None or raw == "":
        return []
    if isinstance(raw, (str, int)):
        s = str(raw).strip()
        if not s or s == "*":
            return []
        raw = [s]
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="Некорректный формат подразделений")
    out: list[int] = []
    for x in raw:
        try:
            did = int(x)
        except (TypeError, ValueError):
            continue
        if did not in out:
            out.append(did)
    return out


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

    # ✅ НОВЫЕ ПОЛЯ (этап 4): специальные права (пока не влияют на логику)
    can_approve: bool = False
    can_edit_references: bool = False
    can_view_salary: bool = False
    can_import: bool = False
    can_manage_users: bool = False
    can_view_all_tabels: bool = False

    @model_validator(mode="before")
    @classmethod
    def _fill_from_orm(cls, values):
        # В модели SQLAlchemy новое поле этапа 3 называется allowed_department_ids_json.
        # Pydantic с from_attributes читает атрибуты по именам полей схемы; имя
        # allowed_department_ids в ORM занято property (список id из JSON-колонки).
        # ✅ ЭТАП 10: старые булевы поля удалены — берём только новые поля модели.
        if isinstance(values, dict):
            return values
        data = {}
        for k in ("id", "username", "full_name", "role", "data_scope",
                  "can_approve", "can_edit_references", "can_view_salary",
                  "can_import", "can_manage_users", "can_view_all_tabels",
                  "permissions"):
            data[k] = getattr(values, k)
        data["allowed_department_ids"] = list(getattr(values, "allowed_department_ids", []) or [])
        return data

    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)
    allowed_department_ids: Optional[List[int]] = None  # ✅ НОВОЕ ПОЛЕ (этап 3/10)

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
    # ✅ ЭТАП 10: только новая система прав (role, data_scope, can_*, permissions)
    role: str = 'user'
    data_scope: str = 'own'
    allowed_department_ids: Optional[List[int]] = None
    can_approve: bool = False
    can_edit_references: bool = False
    can_view_salary: bool = False
    can_import: bool = False
    can_manage_users: bool = False
    can_view_all_tabels: bool = False
    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)


class UserUpdate(BaseModel):
    password: Optional[str] = None
    full_name: Optional[str] = None
    # ✅ ЭТАП 10: только новая система прав; None = «не менять»
    role: Optional[str] = None
    data_scope: Optional[str] = None
    allowed_department_ids: Optional[List[int]] = None
    can_approve: Optional[bool] = None
    can_edit_references: Optional[bool] = None
    can_view_salary: Optional[bool] = None
    can_import: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_view_all_tabels: Optional[bool] = None
    permissions: Optional[List[str]] = None  # ✅ Права доступа к вкладкам (null — все страницы)


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
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Только администратор")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Логин уже существует")
    new_user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        data_scope=payload.data_scope,
        # ✅ ЭТАП 10: подразделения — только новая JSON-колонка (список id)
        allowed_department_ids_json=_normalize_dept_ids(payload.allowed_department_ids),
        can_approve=payload.can_approve,
        can_edit_references=payload.can_edit_references,
        can_view_salary=payload.can_view_salary,
        can_import=payload.can_import,
        can_manage_users=payload.can_manage_users,
        can_view_all_tabels=payload.can_view_all_tabels,
        permissions=payload.permissions,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Только администратор")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        target.hashed_password = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    # ✅ ЭТАП 10: allowed_department_ids (список из схемы) сохраняем в JSON-колонку модели
    if "allowed_department_ids" in data:
        data["allowed_department_ids_json"] = _normalize_dept_ids(data.pop("allowed_department_ids"))
    if "permissions" in data and data["permissions"] is not None and not isinstance(data["permissions"], list):
        raise HTTPException(status_code=400, detail="Недопустимый формат прав доступа")
    for k, v in data.items():
        setattr(target, k, v)
    db.commit()
    db.refresh(target)
    return target
