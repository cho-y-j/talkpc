from typing import Optional
from pydantic import BaseModel


class CreditGrant(BaseModel):
    amount: int
    description: str = ""


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    name: Optional[str] = None
