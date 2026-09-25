import os
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def can_manage_tabels(user: User) -> bool:
    """Создавать и удалять табели могут: Администратор/Кадровик с ролью
    «Инспектор табелей», а также любой пользователь с ролью «Пользователь»."""
    if user.is_user:
        return True
    is_manager = user.is_admin or user.is_hr
    return bool(is_manager and user.timesheet_inspector)


def require_timesheet_inspector(user: User = Depends(get_current_user)) -> User:
    """Доступ для роли «Пользователь» либо «Инспектор табелей» (администратор/кадровик)."""
    if not can_manage_tabels(user):
        raise HTTPException(
            status_code=403,
            detail="Требуются роли «Пользователь» или «Инспектор табелей»",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Доступ только для Администратора."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Только администратор")
    return user


def allowed_department_id_set(user: User, db: Session) -> set[int] | None:
    """Разрешённые id подразделений пользователя (включая дочерние).

    Возвращает None, если пользователю доступны ВСЕ подразделения
    (администратор, кадровик, инспектор табелей или явный «*»).
    Пустое множество — подразделений не назначено.
    """
    from app.models.department import Department

    if user.is_admin or user.is_hr or user.timesheet_inspector or user.all_departments_allowed:
        return None
    base_ids = set(user.allowed_department_ids)
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
