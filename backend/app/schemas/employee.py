from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class EmployeeCreate(BaseModel):
    tab_number: str
    full_name: str
    department_id: Optional[int] = None
    schedule_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    schedule_id: Optional[int] = None


class EmployeeResponse(BaseModel):
    id: int
    tab_number: str
    full_name: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    schedule_id: Optional[int]

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