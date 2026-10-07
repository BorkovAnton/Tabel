"""API раздела «Документы и приказы».

События сотрудников (отпуск, командировка, больничный) с датами и кодом часов.
Эти данные используются автозаполнением табеля («Заполнить по графику») —
активные документы имеют приоритет над графиком работы.
"""
import calendar
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_documents_manager
from app.database import get_db
from app.models.document import Document
from app.models.employee import Employee
from app.schemas.document import DocumentCreate, DocumentOut, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["Documents"])


def _to_out(d: Document) -> DocumentOut:
    emp = d.employee
    return DocumentOut(
        id=d.id,
        employee_id=d.employee_id,
        doc_type=d.doc_type,
        doc_type_category=d.doc_type_category,
        title=d.title or "",
        doc_number=d.doc_number or "",
        start_date=d.start_date,
        end_date=d.end_date,
        code=d.code,
        hours=float(d.hours) if d.hours is not None else None,
        is_active=d.is_active,
        created_at=d.created_at,
        employee_full_name=emp.full_name if emp else "",
        employee_tab_number=emp.tab_number if emp else "",
    )


@router.get("/", response_model=List[DocumentOut])
def list_documents(
    employee_id: Optional[int] = Query(None),
    doc_type: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(Document)
    if not include_inactive:
        q = q.filter(Document.is_active.is_(True))
    if employee_id is not None:
        q = q.filter(Document.employee_id == employee_id)
    if doc_type:
        q = q.filter(Document.doc_type == doc_type)
    if department_id is not None:
        q = q.join(Employee, Document.employee_id == Employee.id).filter(
            Employee.department_id == department_id
        )
    docs = q.all()
    # фильтр по месяцу: пересекающиеся с периодом документы
    if year is not None and month is not None:
        m_start = date(year, month, 1)
        m_end = date(year, month, calendar.monthrange(year, month)[1])
        docs = [d for d in docs if d.start_date <= m_end and d.end_date >= m_start]
    docs.sort(key=lambda d: (d.start_date, d.id), reverse=True)
    return [_to_out(d) for d in docs]


@router.post("/", response_model=DocumentOut)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_documents_manager),
):
    emp = db.get(Employee, payload.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Дата окончания должна быть не раньше даты начала")
    doc = Document(
        employee_id=payload.employee_id,
        doc_type=payload.doc_type,
        doc_type_category=payload.doc_type_category,
        title=(payload.title or "").strip(),
        doc_number=(payload.doc_number or "").strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        code=payload.code,
        hours=payload.hours,
        is_active=payload.is_active,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _to_out(doc)


@router.put("/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_documents_manager),
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    data = payload.model_dump(exclude_unset=True)
    if "employee_id" in data and not db.get(Employee, data["employee_id"]):
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    start = data.get("start_date", doc.start_date)
    end = data.get("end_date", doc.end_date)
    if end < start:
        raise HTTPException(status_code=422, detail="Дата окончания должна быть не раньше даты начала")
    for field, value in data.items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return _to_out(doc)


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_documents_manager),
):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    db.delete(doc)
    db.commit()
    return {"ok": True}
