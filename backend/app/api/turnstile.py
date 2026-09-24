from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, time
import pandas as pd
import io

from app.database import get_db
from app.models.employee import Employee
from app.models.turnstile_event import TurnstileEvent
from app.schemas.turnstile import (
    TurnstileEventResponse,
    TurnstileImportResponse,
    TurnstileImportStats,
    TurnstileImportError,
)


router = APIRouter(prefix="/api/turnstile", tags=["Turnstile"])


# ---------------------------------------------------------------------------
# Вспомогательные функции распознавания ФИО и разбора даты/типа события
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Приводит ФИО к нижнему регистру и убирает лишние пробелы."""
    return " ".join(str(name).strip().lower().split())


def tokenize_name(name: str) -> List[str]:
    """Разбивает ФИО на токены: слова и инициалы (по точкам).

    "Иванов И.И." -> ["Иванов", "И", "И"]
    "Иванов Иван Иванович" -> ["Иванов", "Иван", "Иванович"]
    """
    tokens: List[str] = []
    for word in str(name).strip().split():
        for part in word.split('.'):
            part = part.strip()
            if part:
                tokens.append(part)
    return tokens


def names_partial_match(raw_tokens: List[str], db_tokens: List[str]) -> bool:
    """Проверяет частичное совпадение: фамилия совпадает, а остальные
    токены (имя/отчество) совпадают полностью или по инициалу."""
    if not raw_tokens or not db_tokens:
        return False

    # Фамилия (первый токен) должна совпадать точно
    if raw_tokens[0].lower() != db_tokens[0].lower():
        return False

    db_idx = 1
    for rt in raw_tokens[1:]:
        if db_idx >= len(db_tokens):
            return False
        dt = db_tokens[db_idx]
        rt_l, dt_l = rt.lower(), dt.lower()
        if len(rt_l) == 1:
            # Сравнение по инициалу
            if not dt_l or dt_l[0] != rt_l:
                return False
        else:
            if dt_l != rt_l and not dt_l.startswith(rt_l):
                return False
        db_idx += 1
    return True


def find_employee_by_name(raw_name: str, employees: List[Employee]) -> Optional[Employee]:
    """Ищет сотрудника по ФИО: сначала точное совпадение, затем частичное."""
    normalized_raw = normalize_name(raw_name)
    if not normalized_raw:
        return None

    # 1. Точное совпадение
    for emp in employees:
        if normalize_name(emp.full_name) == normalized_raw:
            return emp

    # 2. Частичное совпадение (например "Иванов И.И." -> "Иванов Иван Иванович")
    raw_tokens = tokenize_name(raw_name)
    for emp in employees:
        db_tokens = tokenize_name(emp.full_name)
        if names_partial_match(raw_tokens, db_tokens) or names_partial_match(db_tokens, raw_tokens):
            return emp

    return None


DATETIME_FORMATS = [
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
]


def parse_turnstile_datetime(value) -> datetime:
    """Разбирает дату/время из ячейки Excel.

    Поддерживает:
    - объекты datetime/Timestamp (когда pandas/openpyxl сам распознал дату)
    - строки формата "ДД.ММ.ГГГГ ЧЧ:ММ" или "ГГГГ-ММ-ДД ЧЧ:ММ:СС"
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("Пустое значение даты/времени")

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(
        f"Неверный формат даты/времени: '{text}'. Ожидается 'ДД.ММ.ГГГГ ЧЧ:ММ' или 'ГГГГ-ММ-ДД ЧЧ:ММ:СС'"
    )


EVENT_TYPE_MAP = {
    "in": "in",
    "out": "out",
    "вход": "in",
    "выход": "out",
}


def normalize_event_type(value) -> str:
    """Приводит тип события к 'in'/'out'."""
    text = str(value).strip().lower()
    if text not in EVENT_TYPE_MAP:
        raise ValueError(
            f"Неизвестный тип события: '{value}'. Ожидается 'in'/'out' или 'Вход'/'Выход'"
        )
    return EVENT_TYPE_MAP[text]


# ---------------------------------------------------------------------------
# Эндпоинты
# ---------------------------------------------------------------------------

@router.post("/import", response_model=TurnstileImportResponse)
async def import_turnstile_events(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Импорт событий проходной (турникета) из Excel-файла."""

    # Проверка формата файла
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Требуется Excel (.xlsx или .xls)"
        )

    # Чтение файла
    try:
        contents = await file.read()
        # Пропускаем первые 4 строки метаданных (Период, Подразделение, Сотрудник, -)
        # Заголовки в строке 5 (index=4)
        df = pd.read_excel(io.BytesIO(contents), header=4)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка чтения файла: {str(e)}"
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Файл пустой или не содержит данных"
        )

    # Проверка наличия обязательных колонок
    required_columns = ['Сотрудник', 'Дата и время', 'Направление']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}. "
                   f"Ожидаемые колонки: {', '.join(required_columns)}"
        )

    stats = TurnstileImportStats(total=len(df), recognized=0, unrecognized=0, errors=0)
    errors: List[TurnstileImportError] = []
    skipped_duplicates = 0  # ← НОВОЕ: счётчик пропущенных дубликатов

    # Загружаем список сотрудников один раз, чтобы не дёргать БД на каждой строке
    employees = db.query(Employee).all()

    for idx, row in df.iterrows():
        try:
            raw_name = str(row['Сотрудник']).strip() if pd.notna(row.get('Сотрудник')) else ""
            raw_datetime = row.get('Дата и время')
            raw_type = row.get('Направление')

            # Пропускаем полностью пустые строки
            is_empty_dt = raw_datetime is None or (
                not isinstance(raw_datetime, (datetime, pd.Timestamp)) and pd.isna(raw_datetime)
            )
            if not raw_name and is_empty_dt:
                continue

            if not raw_name:
                raise ValueError("Не заполнено ФИО")
            if is_empty_dt:
                raise ValueError("Не заполнена дата/время")
            if raw_type is None or (isinstance(raw_type, float) and pd.isna(raw_type)) or not str(raw_type).strip():
                raise ValueError("Не заполнен тип события")

            event_datetime = parse_turnstile_datetime(raw_datetime)
            event_type = normalize_event_type(raw_type)

            employee = find_employee_by_name(raw_name, employees)

            # ← НОВОЕ: Проверка на дубликаты (с точностью до минуты)
            if employee:
                # Округляем время до минуты для сравнения
                dt_minute = event_datetime.replace(second=0, microsecond=0)
                
                existing = db.query(TurnstileEvent).filter(
                    TurnstileEvent.employee_id == employee.id,
                    TurnstileEvent.event_type == event_type,
                    func.date_trunc('minute', TurnstileEvent.datetime) == dt_minute
                ).first()
                
                if existing:
                    # Дубликат найден — пропускаем
                    skipped_duplicates += 1
                    continue

            event = TurnstileEvent(
                raw_name=raw_name,
                employee_id=employee.id if employee else None,
                event_type=event_type,
                datetime=event_datetime,
                is_recognized=employee is not None,
            )
            db.add(event)
            db.commit()

            if employee:
                stats.recognized += 1
            else:
                stats.unrecognized += 1

        except Exception as e:
            db.rollback()
            stats.errors += 1
            # +6: первые 4 строки метаданные + заголовок + нумерация с 1
            errors.append(TurnstileImportError(row=idx + 6, message=str(e)))

    # ← НОВОЕ: Добавляем информацию о пропущенных дубликатах в ответ
    return TurnstileImportResponse(
        stats=stats, 
        errors=errors,
        skipped_duplicates=skipped_duplicates  # ← НОВОЕ поле
    )


@router.get("", response_model=List[TurnstileEventResponse])
def get_turnstile_events(
    employee_id: Optional[int] = Query(None, description="ID сотрудника"),
    date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Получить события турникета сотрудника за указанную дату."""
    query = db.query(TurnstileEvent)

    if employee_id is not None:
        query = query.filter(TurnstileEvent.employee_id == employee_id)

    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Неверный формат даты. Ожидается YYYY-MM-DD"
            )
        start = datetime.combine(day, time.min)
        end = datetime.combine(day, time.max)
        query = query.filter(TurnstileEvent.datetime >= start, TurnstileEvent.datetime <= end)

    events = query.order_by(TurnstileEvent.datetime).all()
    return events


@router.get("/unrecognized", response_model=List[TurnstileEventResponse])
def get_unrecognized_events(db: Session = Depends(get_db)):
    """Получить список нераспознанных записей проходной."""
    events = (
        db.query(TurnstileEvent)
        .filter(TurnstileEvent.is_recognized == False)  # noqa: E712
        .order_by(TurnstileEvent.datetime.desc())
        .all()
    )
    return events

@router.post("/", response_model=TurnstileEventResponse)
def create_turnstile_event(
    event_data: dict,
    db: Session = Depends(get_db)
):
    """Создать событие проходной вручную"""
    
    try:
        raw_name = event_data.get('raw_name', '').strip()
        datetime_str = event_data.get('datetime', '').strip()
        event_type = event_data.get('event_type', '').strip().lower()
        employee_id = event_data.get('employee_id')
        
        if not raw_name or not datetime_str or not event_type:
            raise ValueError("Заполните все обязательные поля")
        
        if event_type not in ['in', 'out']:
            raise ValueError("Тип события должен быть 'in' или 'out'")
        
        # Парсим дату
        event_datetime = parse_turnstile_datetime(datetime_str)
        
        # Ищем сотрудника (если указан ID)
        employee = None
        if employee_id:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                raise ValueError(f"Сотрудник с ID {employee_id} не найден")
        
        # Создаём событие
        event = TurnstileEvent(
            raw_name=raw_name,
            employee_id=employee.id if employee else None,
            event_type=event_type,
            datetime=event_datetime,
            is_recognized=employee is not None
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        return event
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
