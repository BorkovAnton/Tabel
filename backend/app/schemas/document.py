from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


DOC_TYPE_DEFAULT_CODE = {
    "vacation": "О",          # отпуск
    "business_trip": "К",     # командировка
    "sick": "Б",              # больничный
}


def default_code_for_type(doc_type: str) -> str:
    return DOC_TYPE_DEFAULT_CODE.get(doc_type, "")


class DocumentBase(BaseModel):
    employee_id: int
    doc_type: str
    title: str = ""
    doc_number: str = ""
    start_date: date
    end_date: date
    code: str
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Укажите код часов для этого документа")
        return v.upper() if len(v) <= 1 else v

    @field_validator("end_date")
    @classmethod
    def _dates_order(cls, v: date, info):
        start = info.data.get("start_date")
        if start is not None and v < start:
            raise ValueError("Дата окончания должна быть не раньше даты начала")
        return v


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    employee_id: Optional[int] = None
    doc_type: Optional[str] = None
    title: Optional[str] = None
    doc_number: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentOut(DocumentBase):
    id: int
    created_at: Optional[date] = None
    employee_full_name: str = ""
    employee_tab_number: str = ""

    class Config:
        from_attributes = True
