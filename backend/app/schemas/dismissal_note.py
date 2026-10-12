from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel, field_validator


class DismissalDayRecordCreate(BaseModel):
    day: int
    time_out: Optional[str] = None
    time_in: Optional[str] = None
    comment: Optional[str] = None


class DismissalEntryCreate(BaseModel):
    employee_id: int
    day_records: List[DismissalDayRecordCreate] = []


class DismissalNoteCreate(BaseModel):
    period_start: date
    period_end: date
    department_id: Optional[int] = None
    comment: Optional[str] = None
    entries: List[DismissalEntryCreate] = []

    @field_validator('period_end')
    @classmethod
    def validate_period(cls, v, info):
        if 'period_start' in info.data and v < info.data['period_start']:
            raise ValueError('Дата окончания не может быть раньше даты начала')
        return v


class DismissalDayRecordResponse(BaseModel):
    id: int
    day: int
    time_out: Optional[str] = None
    time_in: Optional[str] = None
    hours: float = 0
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class DismissalEntryResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_tab_number: Optional[str] = None
    department_name: Optional[str] = None
    day_records: List[DismissalDayRecordResponse] = []
    total_hours: float = 0

    class Config:
        from_attributes = True


class DismissalNoteResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[str] = None
    entries: List[DismissalEntryResponse] = []
    total_hours: float = 0

    class Config:
        from_attributes = True
