import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator, model_validator, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional, Union

from app.api.auth import _normalize_allowed_departments
from app.core.security import hash_password, require_admin
from app.database import get_db
from app.models.department import Department
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# ✅ Допустимые ключи вкладок сайта (путь страницы). Пустой путь "/" — главная (Сводка).
ALLOWED_PAGE_KEYS = {
    "/", "/tabels", "/employees", "/import", "/turnstile-fix", "/timesheet-report",
    "/hours-report", "/departments", "/schedules", "/settings", "/dismissal-notes",
    "/documents", "/users", "/time-codes",
}

# ✅ FIX 422: допустимые ключи ролей и областей видимости данных.
# Фронтенд должен присылать именно ключ ('admin', 'hr', ...), а не отображаемое имя.
# Валидаторы ниже также терпимо принимают отображаемые русские имена (обратная совместимость).
ALLOWED_ROLE_KEYS = {"none", "user", "manager", "hr", "inspector", "accountant", "admin"}
ROLE_LABEL_TO_KEY = {
    "пользователь (только свои)": "user",
    "пользователь": "user",
    "начальник участка": "manager",
    "кадровик": "hr",
    "инспектор табелей": "inspector",
    "бухгалтер": "accountant",
    "администратор": "admin",
}
ALLOWED_DATA_SCOPE_KEYS = {"own", "department", "custom", "all"}
DATA_SCOPE_LABEL_TO_KEY = {
    "только свои табели": "own",
    "своё подразделение": "department",
    "выбранные подразделения": "custom",
    "все подразделения": "all",
}


def _validation_detail(exc: RequestValidationError) -> str:
    """Человекочитаемое описание ошибок валидации для клиента и логов."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body",))
        parts.append(f"{loc or '<тело>'}: {err.get('msg')}")
    return "; ".join(parts) or "Ошибка валидации запроса"


async def _log_validation_error(request: Request, exc: RequestValidationError):
    """✅ FIX 422: при ошибке валидации логируем точное тело запроса и причину.

    FastAPI по умолчанию возвращает 422 без попадания в код endpoint'а — этот
    обработчик router-level позволяет увидеть в логах бэкенда, ЧТО ИМЕННО
    прислал фронтенд и на каком поле сломалась валидация.
    """
    body_raw = await request.body()
    logger.error(
        "422 Unprocessable Entity: %s %s | ошибки валидации: %s | тело запроса: %s",
        request.method, request.url.path, _validation_detail(exc),
        body_raw.decode("utf-8", errors="replace"),
    )
    # Возвращаем стандартный ответ 422 с человекочитаемым описанием в detail.
    return JSONResponse(status_code=422, content={"detail": _validation_detail(exc)})


def _normalize_permissions(raw) -> Optional[List[str]]:
    """Валидирует и нормализует список прав доступа к вкладкам.

    None/пусто -> None (доступны все страницы — обратная совместимость).
    Бросает HTTPException(400) на недопустимом ключе.
    """
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="Недопустимый формат прав доступа")
    clean: List[str] = []
    for item in raw:
        key = str(item or "").strip()
        if not key:
            continue
        if key not in ALLOWED_PAGE_KEYS:
            raise HTTPException(status_code=400, detail=f"Недопустимое право: {key}")
        if key not in clean:
            clean.append(key)
    return clean or None


class RoleFlags(BaseModel):
    # ✅ НОВОЕ ПОЛЕ (этап 1): единая роль (пока не влияет на логику).
    # Optional: None означает «не менять» при обновлении.
    role: Optional[str] = None
    # ✅ НОВЫЕ ПОЛЯ (этап 3): область видимости данных (пока не влияет на логику).
    # Optional: None означает «не менять» при обновлении.
    data_scope: Optional[str] = None
    allowed_department_ids_json: Optional[List[int]] = None
    # ✅ ЭТАП 5: фронтенд может прислать allowed_department_ids — принимаем как алиас,
    # чтобы форма пользователя могла сохранять список подразделений в новой JSON-колонке.
    allowed_department_ids: Optional[List[int]] = Field(default=None)

    @model_validator(mode="after")
    def _sync_allowed_dept_alias(self):
        if self.allowed_department_ids is not None and self.allowed_department_ids_json is None:
            self.allowed_department_ids_json = self.allowed_department_ids
        return self

    # ✅ НОВЫЕ ПОЛЯ (этап 4): специальные права (пока не влияют на логику).
    # В RoleFlags — только как Optional (None = «не менять»), чтобы существующие
    # клиенты, не присылающие эти поля, не сбрасывали их в false при обновлении.
    can_approve: Optional[bool] = None
    can_edit_references: Optional[bool] = None
    can_view_salary: Optional[bool] = None
    can_import: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_view_all_tabels: Optional[bool] = None
    # ✅ СТАРЫЕ ПОЛЯ (продолжают работать)
    is_admin: bool = False            # Администратор
    is_hr: bool = False               # Кадровик
    timesheet_inspector: bool = False # Инспектор табелей
    is_user: bool = True              # Пользователь (базовая роль)
    is_report: bool = False           # Отчёт (страница сводного отчёта часов)
    is_documents_manager: bool = False  # Документы и приказы
    # ✅ Права доступа к вкладкам: список путей или null (все страницы)
    permissions: Optional[List[str]] = None
    # Права на подразделения: JSON-строка '["*"]'-список id или "*" (все).
    # Фронтенд может прислать и список чисел — нормализуем валидатором.
    allowed_departments: str = ""

    @field_validator("allowed_departments", mode="before")
    @classmethod
    def _ad_to_str(cls, v):
        if v is None:
            return ""
        if isinstance(v, list):
            return json.dumps([int(x) for x in v])
        return str(v)

    # ✅ FIX 422: терпимая нормализация роли — принимаем ключ ('admin', 'hr', ...),
    # отображаемое имя ('Администратор', 'Кадровик', ...) или пустое значение.
    # Неизвестное значение -> 'user' (безопасный дефолт вместо падения с 422).
    @field_validator("role", mode="before")
    @classmethod
    def _normalize_role(cls, v):
        if v is None:
            return None
        s = str(v).strip().lower()
        if not s or s == "none":
            return "none" if s == "none" else None
        if s in ALLOWED_ROLE_KEYS:
            return s
        mapped = ROLE_LABEL_TO_KEY.get(s)
        if mapped:
            logger.warning("role прислана отображаемым именем %r — нормализовано в %r", v, mapped)
            return mapped
        logger.warning("Неизвестная роль %r — использован безопасный дефолт 'user'", v)
        return "user"

    # ✅ FIX 422: аналогично для data_scope; неизвестное значение -> 'own'.
    @field_validator("data_scope", mode="before")
    @classmethod
    def _normalize_data_scope(cls, v):
        if v is None:
            return None
        s = str(v).strip().lower()
        if not s:
            return None
        if s in ALLOWED_DATA_SCOPE_KEYS:
            return s
        mapped = DATA_SCOPE_LABEL_TO_KEY.get(s)
        if mapped:
            logger.warning("data_scope прислано отображаемым именем %r — нормализовано в %r", v, mapped)
            return mapped
        logger.warning("Неизвестный data_scope %r — использован безопасный дефолт 'own'", v)
        return "own"

    # ✅ FIX 422: если фронтенд прислал id подразделений строками ("1","2"),
    # конвертируем в int; нечисловые значения отбрасываем, а не роняем запрос с 422.
    @field_validator("allowed_department_ids", "allowed_department_ids_json", mode="before")
    @classmethod
    def _normalize_dept_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, (str, int)):
            v = [v]
        if isinstance(v, list):
            out = []
            for x in v:
                try:
                    out.append(int(x))
                except (TypeError, ValueError):
                    logger.warning("Отброшено нечисловое значение id подразделения: %r", x)
            return out
        logger.warning("Некорректный формат allowed_department_ids: %r — сброшено в []", v)
        return []


class UserWithRoles(RoleFlags):
    id: int
    username: str
    full_name: str
    # ✅ НОВОЕ ПОЛЕ (этап 1): в ответе всегда строка (по умолчанию 'user')
    role: str = 'user'

    @field_validator("role", mode="before")
    @classmethod
    def _role_default(cls, v):
        # Обратная совместимость: если в БД NULL — считаем 'user'
        return v if v else "user"

    # ✅ НОВОЕ ПОЛЕ (этап 3): в ответе всегда строка (по умолчанию 'own')
    data_scope: str = 'own'

    @field_validator("data_scope", mode="before")
    @classmethod
    def _data_scope_default(cls, v):
        # Обратная совместимость: если в БД NULL — считаем 'own'
        return v if v else "own"

    allowed_department_names: List[str] = []
    all_departments: bool = False

    @model_validator(mode="after")
    def _fill_dept_ids_alias(self):
        # ✅ ЭТАП 5: для ответа API заполняем allowed_department_ids из новой JSON-колонки,
        # чтобы фронтенд мог редактировать список подразделений новой системы.
        if self.allowed_department_ids is None:
            self.allowed_department_ids = list(self.allowed_department_ids_json or [])
        return self

    class Config:
        from_attributes = True


class UserCreateWithRoles(RoleFlags):
    username: str
    password: str
    full_name: str = ""
    # ✅ НОВОЕ ПОЛЕ (этап 1): при создании всегда конкретная роль
    role: str = 'user'
    # ✅ НОВОЕ ПОЛЕ (этап 3): при создании всегда конкретная область данных
    data_scope: str = 'own'

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


def _dept_names_map(db: Session) -> dict:
    return {d.id: d.name for d in db.query(Department).all()}


def _to_with_roles(u: User, names: dict) -> UserWithRoles:
    obj = UserWithRoles.model_validate(u)
    if u.all_departments_allowed:
        obj.all_departments = True
        obj.allowed_department_names = ["Все подразделения"]
    else:
        obj.allowed_department_names = [names.get(i, f"#{i}") for i in u.allowed_department_ids]
    return obj

@router.get("/with-roles", response_model=List[UserWithRoles])
def list_users_with_roles(db: Session = Depends(get_db),
                          user: User = Depends(require_admin)):
    """Справочник пользователей с ролями — только для Администратора."""
    names = _dept_names_map(db)
    return [_to_with_roles(u, names)
            for u in db.query(User).order_by(User.username).all()]


@router.post("/with-roles", response_model=UserWithRoles)
def create_user_with_roles(payload: UserCreateWithRoles, db: Session = Depends(get_db),
                           user: User = Depends(require_admin)):
    """Добавление пользователя с ролями — только для Администратора."""
    logger.info("Создание пользователя: admin_id=%s, данные запроса: %s",
                user.id, json.dumps(payload.model_dump(), ensure_ascii=False, default=str))
    try:
        username = payload.username.strip()
        if db.query(User).filter(User.username == username).first():
            raise HTTPException(status_code=400, detail=f"Логин «{username}» уже существует")
        obj = User(
            username=username,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=payload.role,  # ✅ НОВОЕ ПОЛЕ (этап 1)
            data_scope=payload.data_scope,  # ✅ НОВОЕ ПОЛЕ (этап 3)
            allowed_department_ids_json=payload.allowed_department_ids_json,  # ✅ НОВОЕ ПОЛЕ (этап 3)
            # ✅ НОВЫЕ ПОЛЯ (этап 4): специальные права (None -> False при создании)
            can_approve=payload.can_approve or False,
            can_edit_references=payload.can_edit_references or False,
            can_view_salary=payload.can_view_salary or False,
            can_import=payload.can_import or False,
            can_manage_users=payload.can_manage_users or False,
            can_view_all_tabels=payload.can_view_all_tabels or False,
            is_admin=payload.is_admin,
            is_hr=payload.is_hr,
            timesheet_inspector=payload.timesheet_inspector,
            is_user=payload.is_user,
            is_report=payload.is_report,
            is_documents_manager=payload.is_documents_manager,
            permissions=_normalize_permissions(payload.permissions),  # ✅ НОВОЕ ПОЛЕ
            allowed_departments=_normalize_allowed_departments(payload.allowed_departments, db),
        )
        # ✅ ЭТАП 7: безопасный дефолт — если задана роль, но is_user явно не включён,
        # автоматически ставим is_user = True (старые части кода зависят от этого поля)
        if obj.role and not obj.is_user:
            obj.is_user = True
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _to_with_roles(obj, _dept_names_map(db))
    except HTTPException:
        # 400 и т.п. отдаём клиенту как есть, но пишем в лог, что именно прислал фронтенд
        logger.error("Ошибка при создании пользователя %r: получены данные: %s",
                     payload.username,
                     json.dumps(payload.model_dump(), ensure_ascii=False, default=str))
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Ошибка БД при создании пользователя: %s", e)
        logger.error("Полученные данные: %s",
                     json.dumps(payload.model_dump(), ensure_ascii=False, default=str))
        raise HTTPException(status_code=400, detail=f"Ошибка сохранения пользователя: {e}")


@router.put("/with-roles/{user_id}", response_model=UserWithRoles)
def update_user_with_roles(user_id: int, payload: RoleFlags, db: Session = Depends(get_db),
                           user: User = Depends(require_admin)):
    """Редактирование ролей и прав на подразделения — только для Администратора."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    # ✅ НОВОЕ ПОЛЕ (этап 1): role — Optional[str]; None означает «не менять»
    data = payload.model_dump(exclude_unset=True)
    new_role = data.pop("role", None)
    if new_role is not None:
        target.role = new_role
    # ✅ НОВЫЕ ПОЛЯ (этап 3): data_scope / allowed_department_ids_json — None = «не менять»
    new_data_scope = data.pop("data_scope", None)
    if new_data_scope is not None:
        target.data_scope = new_data_scope
    if "allowed_department_ids_json" in data:
        target.allowed_department_ids_json = data.pop("allowed_department_ids_json")
    # ✅ ЭТАП 5: алиас из фронтенда не является колонкой модели — убираем, чтобы не попасть в setattr ниже
    data.pop("allowed_department_ids", None)
    # ✅ НОВЫЕ ПОЛЯ (этап 4): специальные права — None = «не менять»,
    # чтобы старые клиенты, не присылающие эти поля, ничего не сбросили.
    for _perm_field in ("can_approve", "can_edit_references", "can_view_salary",
                        "can_import", "can_manage_users", "can_view_all_tabels"):
        if _perm_field in data:
            setattr(target, _perm_field, bool(data[_perm_field]))
    target.is_admin = payload.is_admin
    target.is_hr = payload.is_hr
    target.timesheet_inspector = payload.timesheet_inspector
    target.is_user = payload.is_user
    target.is_report = payload.is_report
    target.is_documents_manager = payload.is_documents_manager
    # ✅ ЭТАП 7: безопасный дефолт — если роль задана (не 'none'), а is_user не включён,
    # автоматически ставим is_user = True, чтобы старые части кода не ломались
    effective_role = new_role if new_role is not None else target.role
    if effective_role and effective_role != 'none' and not target.is_user:
        target.is_user = True
    # ✅ НОВОЕ: обновление прав доступа к вкладкам (None — все страницы)
    target.permissions = _normalize_permissions(payload.permissions)
    target.allowed_departments = _normalize_allowed_departments(payload.allowed_departments, db)
    db.commit()
    db.refresh(target)
    return _to_with_roles(target, _dept_names_map(db))


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
