import os
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _extract_token(authorization: str | None, token_param: str | None) -> str | None:
    """JWT из заголовка Authorization: Bearer ... либо из query-параметра access_token.

    Query-параметр нужен для запросов navigator.sendBeacon (автосохранение КДУ
    при закрытии вкладки), которые не могут отправить заголовок Authorization.
    """
    if authorization:
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() == "bearer" and param:
            return param
    return token_param or None


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Заголовок Authorization: Bearer в приоритете; query-параметр access_token
    # используется как fallback для navigator.sendBeacon (не может ставить заголовки).
    raw_token = _extract_token(None, token or access_token)
    if not raw_token:
        raise credentials_exception
    try:
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# ─── ЭТАП 9: единая система ролей ────────────────────────────────────────────
# Все проверки прав опираются ТОЛЬКО на новые поля: role, data_scope, can_*.
# Старые булевы колонки (is_admin, is_hr, timesheet_inspector, is_user,
# is_report, is_documents_manager) остаются в БД/моделях как «тихий резерв»
# (удалятся на Этапе 10), но логика авторизации их больше НЕ использует.

MANAGE_TABELS_ROLES = {"admin", "hr", "manager", "inspector"}


def has_role(user: User, *roles: str) -> bool:
    """Проверка новой роли пользователя (role)."""
    return bool(user) and getattr(user, "role", None) in roles


def is_admin_user(user: User) -> bool:
    return has_role(user, "admin")


def is_inspector(user: User) -> bool:
    """Инспектор табелей по новой системе: роль inspector/admin/hr
    либо явное право can_view_all_tabels."""
    return has_role(user, "inspector", "admin", "hr") or bool(user.can_view_all_tabels)


def can_manage_tabels(user: User) -> bool:
    """Создавать и редактировать табели могут роли admin/hr/manager/inspector,
    а также любой пользователь с явным правом can_approve."""
    if has_role(user, *MANAGE_TABELS_ROLES):
        return True
    return bool(user.can_approve)


def require_timesheet_inspector(user: User = Depends(get_current_user)) -> User:
    """Доступ для ролей, которым разрешено управление табелями (Этап 9: role/can_*)."""
    if not can_manage_tabels(user):
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав. Требуется роль «Пользователь», «Начальник участка», "
                   "«Инспектор табелей» или право согласования.",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Доступ только для роли «Администратор» (role == 'admin')."""
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль Администратора.",
        )
    return user


def require_hr_or_admin(user: User = Depends(get_current_user)) -> User:
    """Доступ для ролей «Кадровик» или «Администратор»."""
    if not has_role(user, "admin", "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль Кадровика или Администратора.",
        )
    return user


def can_manage_documents(user: User) -> bool:
    """Раздел «Документы и приказы»: роли admin/hr/manager (новая система).

    Начальники участков (manager) могут создавать документы для своих
    сотрудников, но видят только созданные ими документы
    (фильтрация по created_by в GET /documents/), если у них нет
    явного права can_view_all_documents.
    """
    return has_role(user, "admin", "hr", "manager")


def require_documents_manager(user: User = Depends(get_current_user)) -> User:
    """Доступ для создания/редактирования документов и приказов."""
    if not can_manage_documents(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления документами. "
                   "Требуется роль «Администратор», «Кадровик» или «Начальник».",
        )
    return user


def can_see_all_documents(user: User) -> bool:
    """Видит ли пользователь ВСЕ документы/приказы (а не только созданные им).

    Право дают: роли admin/hr, явный флаг can_view_all_documents,
    либо data_scope == 'all' (полная область видимости данных).
    """
    if has_role(user, "admin", "hr"):
        return True
    if getattr(user, "data_scope", None) == "all":
        return True
    return bool(getattr(user, "can_view_all_documents", False))


def can_view_salary(user: User) -> bool:
    """Просмотр зарплатных данных: роли admin/hr/accountant либо флаг can_view_salary."""
    return has_role(user, "admin", "hr", "accountant") or bool(user.can_view_salary)


def require_salary_viewer(user: User = Depends(get_current_user)) -> User:
    if not can_view_salary(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра зарплатных данных.",
        )
    return user


def can_see_all_tabels(user: User) -> bool:
    """Видит ли пользователь ВСЕ табели (а не только свои):
    роли admin/hr/inspector/accountant, scope 'all' или флаг can_view_all_tabels."""
    if has_role(user, "admin", "hr", "inspector", "accountant"):
        return True
    if getattr(user, "data_scope", None) == "all":
        return True
    return bool(user.can_view_all_tabels)


def allowed_department_id_set(user: User, db: Session) -> set[int] | None:
    """Разрешённые id подразделений пользователя (включая дочерние).

    ЭТАП 9: область видимости определяется новыми полями
    role / data_scope / allowed_department_ids_json.

    Возвращает None, если пользователю доступны ВСЕ подразделения;
    пустое множество — конкретные подразделения не заданы.
    """
    from app.models.department import Department

    # 1) Явный список id из новой JSON-колонки (с раскрытием дочерних)
    json_ids = [int(x) for x in (user.allowed_department_ids_json or [])
                if str(x).lstrip("-").isdigit()]
    if json_ids:
        base_ids = set(json_ids)
    elif user.all_departments_allowed:
        # старый текстовый "*" — тихий фолбэк до удаления колонок (Этап 10)
        return None
    else:
        # 2) Роли с полным доступом ко всем подразделениям
        if has_role(user, "admin", "hr", "inspector", "accountant"):
            return None
        # 3) data_scope: 'all' — все подразделения
        scope = getattr(user, "data_scope", "own")
        if scope == "all":
            return None
        # 4) data_scope: 'department' — подразделения, за которые пользователь
        #    отвечает в табелях (собираются из таблицы tabels)
        if scope == "department":
            from app.models.tabel import Tabel

            rows = db.query(Tabel.department_id).filter(
                Tabel.responsible_user_id == user.id
            ).distinct().all()
            base_ids = {int(r[0]) for r in rows if r[0] is not None}
        else:
            # 'own' / 'custom' без списка / отсутствие роли — своих подразделений нет
            return set()
    if not base_ids:
        return set()
    # добавляем все дочерние подразделения рекурсивно
    all_depts = db.query(Department.id, Department.parent_id).all()
    children: dict[int, list[int]] = {}
    for did, pid in all_depts:
        children.setdefault(pid, []).append(did)
    result = set(base_ids)
    stack = list(base_ids)
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child not in result:
                result.add(child)
                stack.append(child)
    return result


def check_department_access(user: User, db: Session, department_id) -> None:
    """403, если пользователю нельзя работать с указанным подразделением."""
    allowed = allowed_department_id_set(user, db)
    if allowed is None:  # все подразделения
        return
    if department_id is None or int(department_id) not in allowed:
        raise HTTPException(status_code=403,
                            detail="Нет прав на это подразделение (права выдаёт администратор)")
