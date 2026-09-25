from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.security import allowed_department_id_set, get_current_user
from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    parent_name: Optional[str] = None
    employee_count: int = 0
    children_count: int = 0
    children: List['DepartmentResponse'] = []

    class Config:
        from_attributes = True


DepartmentResponse.model_rebuild()


def build_tree(departments: List[Department], parent_id: Optional[int], db: Session) -> List[dict]:
    """Рекурсивно строит дерево подразделений"""
    result = []
    for dept in departments:
        if dept.parent_id == parent_id:
            # Считаем сотрудников только в этом подразделении
            direct_employee_count = db.query(Employee).filter(
                Employee.department_id == dept.id
            ).count()
            
            # Считаем дочерние подразделения
            children_count = sum(1 for d in departments if d.parent_id == dept.id)
            
            # Рекурсивно получаем детей
            children = build_tree(departments, dept.id, db)
            
            # Суммируем сотрудников из всех дочерних подразделений
            total_employee_count = direct_employee_count
            for child in children:
                total_employee_count += child.get("employee_count", 0)
            
            # Имя родителя
            parent_name = None
            if dept.parent_id:
                parent = next((d for d in departments if d.id == dept.parent_id), None)
                if parent:
                    parent_name = parent.name
            
            result.append({
                "id": dept.id,
                "name": dept.name,
                "parent_id": dept.parent_id,
                "parent_name": parent_name,
                "employee_count": total_employee_count,  # Общее количество с детьми
                "children_count": children_count,
                "children": children
            })
    return result


@router.get("/", response_model=List[DepartmentResponse])
def get_departments(
    flat: bool = Query(False, description="Плоский список вместо дерева"),
    all: bool = Query(False, description="Все подразделения (для администратора, выдаёт права)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Получить список подразделений.

    Роль «Пользователь» получает только подразделения, на которые у него
    есть права (назначает администратор в справочнике «Пользователи»).
    Флаг all=True возвращает полный список — доступен только администратору.
    """
    allowed = None if all else allowed_department_id_set(user, db)
    if not all and allowed is not None:
        departments = db.query(Department).filter(Department.id.in_(allowed or [-1])).all()
    else:
        departments = db.query(Department).all()
    
    if flat:
        result = []
        for dept in departments:
            employee_count = db.query(Employee).filter(
                Employee.department_id == dept.id
            ).count()
            children_count = sum(1 for d in departments if d.parent_id == dept.id)
            
            parent_name = None
            if dept.parent_id:
                parent = next((d for d in departments if d.id == dept.parent_id), None)
                if parent:
                    parent_name = parent.name
            
            result.append({
                "id": dept.id,
                "name": dept.name,
                "parent_id": dept.parent_id,
                "parent_name": parent_name,
                "employee_count": employee_count,
                "children_count": children_count,
                "children": []
            })
        return result
    else:
        return build_tree(departments, None, db)


@router.get("/tree")
def get_departments_tree(db: Session = Depends(get_db)):
    """Получить дерево подразделений"""
    departments = db.query(Department).all()
    return build_tree(departments, None, db)


@router.post("/", response_model=DepartmentResponse)
def create_department(department: DepartmentCreate, db: Session = Depends(get_db)):
    """Создать новое подразделение"""
    existing = db.query(Department).filter(Department.name == department.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Подразделение '{department.name}' уже существует"
        )
    
    if department.parent_id:
        parent = db.query(Department).filter(Department.id == department.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Родительское подразделение с ID {department.parent_id} не найдено"
            )
    
    new_dept = Department(
        name=department.name,
        parent_id=department.parent_id
    )
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    
    employee_count = db.query(Employee).filter(
        Employee.department_id == new_dept.id
    ).count()
    
    parent_name = None
    if new_dept.parent_id:
        parent = db.query(Department).filter(Department.id == new_dept.parent_id).first()
        if parent:
            parent_name = parent.name
    
    return {
        "id": new_dept.id,
        "name": new_dept.name,
        "parent_id": new_dept.parent_id,
        "parent_name": parent_name,
        "employee_count": employee_count,
        "children_count": 0,
        "children": []
    }


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    department: DepartmentUpdate,
    db: Session = Depends(get_db)
):
    """Обновить подразделение"""
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")
    
    if department.name is not None:
        existing = db.query(Department).filter(
            Department.name == department.name,
            Department.id != department_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Подразделение '{department.name}' уже существует"
            )
        dept.name = department.name
    
    if department.parent_id is not None:
        if department.parent_id == department_id:
            raise HTTPException(
                status_code=400,
                detail="Подразделение не может быть родителем самого себя"
            )
        if department.parent_id:
            parent = db.query(Department).filter(Department.id == department.parent_id).first()
            if not parent:
                raise HTTPException(
                    status_code=400,
                    detail=f"Родительское подразделение с ID {department.parent_id} не найдено"
                )
        dept.parent_id = department.parent_id
    
    db.commit()
    db.refresh(dept)
    
    employee_count = db.query(Employee).filter(
        Employee.department_id == dept.id
    ).count()
    
    parent_name = None
    if dept.parent_id:
        parent = db.query(Department).filter(Department.id == dept.parent_id).first()
        if parent:
            parent_name = parent.name
    
    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "parent_name": parent_name,
        "employee_count": employee_count,
        "children_count": 0,
        "children": []
    }


@router.delete("/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db)):
    """Удалить подразделение"""
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Подразделение не найдено")
    
    employee_count = db.query(Employee).filter(
        Employee.department_id == department_id
    ).count()
    
    if employee_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя удалить подразделение: в нём {employee_count} сотрудников"
        )
    
    children_count = db.query(Department).filter(
        Department.parent_id == department_id
    ).count()
    
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя удалить подразделение: в нём {children_count} дочерних подразделений"
        )
    
    db.delete(dept)
    db.commit()
    
    return {"status": "ok"}