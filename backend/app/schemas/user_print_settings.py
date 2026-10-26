from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserPrintSettingsResponse(BaseModel):
    id: int
    user_id: int
    selected_columns: Optional[List[str]] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserPrintSettingsUpdate(BaseModel):
    selected_columns: List[str]
