from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import date, datetime


class TimesheetRecordResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    first_in: Optional[datetime] = None
    last_out: Optional[datetime] = None
    fact_hours: float
    planned_hours: Optional[float] = None
    default_hours: float
    overtime: Optional[float] = None
    lunch_minutes: int
    needs_review: bool
    review_reason: Optional[str] = None

    class Config:
        from_attributes = True


class TimesheetDayValue(BaseModel):
    value: str
    hours: float


class TimesheetEmployeeReport(BaseModel):
    index: int
    full_name: str
    department: str
    days: Dict[str, TimesheetDayValue]
    total_hours: float


class TimesheetReportResponse(BaseModel):
    month: int
    year: int
    days_in_month: int
    employees: List[TimesheetEmployeeReport]


class TimesheetCalculateRequest(BaseModel):
    employee_id: Optional[int] = None
    date_from: str
    date_to: str


class TimesheetCalculateResponse(BaseModel):
    total_days: int
    employees_processed: int
    records_created: int
    records_updated: int
    needs_review_count: int


class TimesheetUpdateRequest(BaseModel):
    planned_hours: Optional[float] = None
    needs_review: Optional[bool] = None
    review_reason: Optional[str] = None
