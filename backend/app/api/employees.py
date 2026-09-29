from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import or_, and_, func, String
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io

from app.core.security import require_admin
from app.database import get_db
from app.models.employee import Employee
from app.models.department import Department
from app.models.work_schedule import WorkSchedule
from app.schemas.employee import (
    EmployeeResponse,
    EmployeeImportResponse,
    EmployeeImportStats,
    EmployeeImportError,
    EmployeeCreate,
    EmployeeUpdate
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("/", response_model=List[EmployeeResponse])
def get_employees(
    skip: int = 0,
    limit: int = 3000,
    search: Optional[str] = Query(None, description="Поиск по ФИО / таб. номеру / подразделению"),
    db: Session = Depends(get_db),
):
    """Получить список сотрудников с пагинацией и поиском.

    Логика поиска (минимум 1 символ):
      - регистронезависимо по подстроке (роман находит и «Романов»,
        и «Бельков Роман»), с нормализацией Ё->Е;
      - поля: ФИО, табельный номер, название подразделения.
    """
    query = db.query(Employee)

    if search and len(search.strip()) >= 1:
        q = search.strip()
        norm = lambda expr: func.lower(func.replace(expr, 'Ё', 'Е'))
        like = f"%{q.lower().replace('ё', 'е')}%"
        query = query.outerjoin(Department, Employee.department_id == Department.id).filter(
            or_(
                norm(Employee.full_name).like(like),
                norm(func.cast(Employee.tab_number, String)).like(like),
                norm(Department.name).like(like),
            )
        )

    employees = query.offset(skip).limit(limit).all()
    
    # Добавляем названия подразделений
    result = []
    for emp in employees:
        emp_dict = {
            "id": emp.id,
            "tab_number": emp.tab_number,
            "full_name": emp.full_name,
            "department_id": emp.department_id,
            "schedule_id": emp.schedule_id,
            "norm_hours": float(emp.norm_hours) if emp.norm_hours is not None else None,
            "department_name": None
        }
        
        # Получаем название подразделения
        if emp.department_id:
            dept = db.query(Department).filter(Department.id == emp.department_id).first()
            if dept:
                emp_dict["department_name"] = dept.name
        
        result.append(emp_dict)
    
    return result

@router.post("/", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """Создать нового сотрудника вручную"""
    
    # Проверяем, нет ли уже сотрудника с таким табельным номером
    existing = db.query(Employee).filter(Employee.tab_number == employee.tab_number).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Сотрудник с табельным номером {employee.tab_number} уже существует"
        )
    
    # Создаём сотрудника
    new_employee = Employee(
        tab_number=employee.tab_number,
        full_name=employee.full_name,
        department_id=employee.department_id,
        schedule_id=employee.schedule_id,
        norm_hours=employee.norm_hours
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    
    return new_employee

@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    """Частичное обновление сотрудника (ФИО, подразделение, график)."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    data = employee_update.model_dump(exclude_unset=True)

    # Если меняется табельный номер — проверяем уникальность
    new_tab = data.get("tab_number")
    if new_tab and new_tab != emp.tab_number:
        existing = db.query(Employee).filter(
            Employee.tab_number == new_tab,
            Employee.id != employee_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Сотрудник с табельным номером {new_tab} уже существует"
            )

    for field, value in data.items():
        setattr(emp, field, value)

    db.commit()
    db.refresh(emp)

    dept_name = None
    if emp.department_id:
        dept = db.query(Department).filter(Department.id == emp.department_id).first()
        if dept:
            dept_name = dept.name

    return {
        "id": emp.id,
        "tab_number": emp.tab_number,
        "full_name": emp.full_name,
        "department_id": emp.department_id,
        "schedule_id": emp.schedule_id,
        "norm_hours": float(emp.norm_hours) if emp.norm_hours is not None else None,
        "department_name": dept_name,
    }


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """Удалить сотрудника."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    db.delete(emp)
    db.commit()
    return {"ok": True}


@router.post("/import", response_model=EmployeeImportResponse)
async def import_employees_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Импорт ТОЛЬКО НОВЫХ сотрудников из Excel. Доступ только для Администратора."""
    
    # Проверка формата файла
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Требуется Excel (.xlsx или .xls)"
        )
    
    # Чтение файла
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка чтения файла: {str(e)}"
        )
    
    # Проверка на пустой файл
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Файл пустой или не содержит данных"
        )
    
    # Проверка наличия обязательных колонок (как в вашем файле)
    required_columns = ['ФИО', 'Таб. номер']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}. "
                   f"Ожидаемые колонки: {', '.join(required_columns)}"
        )
    
    # Получаем график работы по умолчанию (первый из справочника)
    default_schedule = db.query(WorkSchedule).order_by(WorkSchedule.id).first()
    default_schedule_id = default_schedule.id if default_schedule else None
    
    stats = EmployeeImportStats(created=0, updated=0, errors=0, total=len(df))
    errors = []
    
    # Обработка каждой строки
    for idx, row in df.iterrows():
        try:
            # Извлекаем данные (как в вашем Excel)
            tab_number = str(row['Таб. номер']).strip() if pd.notna(row.get('Таб. номер')) else ""
            full_name = str(row['ФИО']).strip() if pd.notna(row.get('ФИО')) else ""
            
            # Пропускаем пустые строки
            if not tab_number or not full_name or tab_number == "nan":
                continue
            
            # Проверяем, есть ли уже сотрудник с таким табельным номером
            existing_employee = db.query(Employee).filter(
                Employee.tab_number == tab_number
            ).first()
            
            if existing_employee:
                # Сотрудник уже есть — пропускаем
                stats.updated += 1  # Считаем как "уже существует"
                continue
            
            # Создаём или находим подразделение
            department_id = None
            if 'Текущий участок отдел служба' in df.columns and pd.notna(row.get('Текущий участок отдел служба')):
                dept_name = str(row['Текущий участок отдел служба']).strip()
                if dept_name and dept_name != "nan":
                    department = db.query(Department).filter(
                        Department.name == dept_name
                    ).first()
                    
                    if not department:
                        department = Department(name=dept_name)
                        db.add(department)
                        db.commit()
                        db.refresh(department)
                    
                    department_id = department.id
            
            # Создаём НОВОГО сотрудника с привязкой к графику по умолчанию
            new_employee = Employee(
                tab_number=tab_number,
                full_name=full_name,
                department_id=department_id,
                schedule_id=default_schedule_id  # ← Привязываем к графику по умолчанию
            )
            db.add(new_employee)
            db.commit()
            
            stats.created += 1
            
        except Exception as e:
            errors.append(EmployeeImportError(
                row=idx + 2,  # +2 т.к. нумерация с 1 и есть заголовок
                message=str(e)
            ))
            stats.errors += 1
            db.rollback()
    
    return EmployeeImportResponse(stats=stats, errors=errors)