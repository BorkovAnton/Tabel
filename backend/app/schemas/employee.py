from pydantic import BaseModel
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


class EmployeeResponse(BaseModel):
    id: int
    tab_number: str
    full_name: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    schedule_id: Optional[int]
    norm_hours: Optional[float] = None

    class Config:
        from_attributes = True


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