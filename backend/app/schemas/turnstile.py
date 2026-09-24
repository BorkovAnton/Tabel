from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TurnstileEventResponse(BaseModel):
    id: int
    raw_name: str
    employee_id: Optional[int]
    event_type: str
    datetime: datetime
    is_recognized: bool

    class Config:
        from_attributes = True


class TurnstileImportStats(BaseModel):
    total: int
    recognized: int
    unrecognized: int
    errors: int


class TurnstileImportError(BaseModel):
    row: int
    message: str
    data: Optional[dict] = None


class TurnstileImportResponse(BaseModel):
    stats: TurnstileImportStats
    errors: List[TurnstileImportError]
    skipped_duplicates: int = 0  # ← ДОБАВИТЬ ЭТО ПОЛЕ

    class Config:
        from_attributes = True
