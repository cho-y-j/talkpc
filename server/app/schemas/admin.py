from typing import Optional
from pydantic import BaseModel


class CreditGrant(BaseModel):
    amount: int
    description: str = ""


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    name: Optional[str] = None
    daily_limit: Optional[int] = None
    hourly_limit: Optional[int] = None
    send_start_hour: Optional[int] = None
    send_end_hour: Optional[int] = None
    is_locked: Optional[bool] = None
