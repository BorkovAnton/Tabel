from pydantic import BaseModel, model_validator
from typing import List, Optional
from datetime import datetime


class EmployeeCreate(BaseModel):
    tab_number: str
    full_name: str
    department_id: Optional[int] = None
    schedule_id: Optional[int] = None
    # Резервная норма часов (fallback без графика). По умолчанию NULL — норма берётся из графика.
    norm_hours: Optional[float] = None


class EmployeeUpdate(BaseModel):
    tab_number: Optional[str] = None
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    schedule_id: Optional[int] = None
    norm_hours: Optional[float] = None


def format_short_name(full_name: Optional[str]) -> Optional[str]:
    """Формирует "Фамилия И.О." из полного ФИО."""
    if not full_name:
        return None
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
    if len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return full_name.strip()


class EmployeeResponse(BaseModel):
    id: int
    tab_number: str
    full_name: str
    short_name: Optional[str] = None  # "Фамилия И.О."
    department_id: Optional[int]
    department_name: Optional[str] = None
    schedule_id: Optional[int]
    norm_hours: Optional[float] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _fill_short_name(self):
        if not self.short_name:
            self.short_name = format_short_name(self.full_name)
        return self


class EmployeeImportStats(BaseModel):
    created: int
    updated: int
    errors: int
    total: int


class EmployeeImportError(BaseModel):
    row: int
    message: str
    data: Optional[dict] = None


class EmployeeImportResponse(BaseModel):
    stats: EmployeeImportStats
    errors: List[EmployeeImportError] = []