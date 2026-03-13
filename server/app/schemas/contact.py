from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str
    category: str = "other"
    phone: str = ""
    company: str = ""
    position: str = ""
    memo: str = ""
    birthday: str = ""
    anniversary: str = ""


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    memo: Optional[str] = None
    birthday: Optional[str] = None
    anniversary: Optional[str] = None


class ContactResponse(BaseModel):
    id: int
    name: str
    category: str
    phone: str
    company: str
    position: str
    memo: str
    birthday: str
    anniversary: str
    created_at: datetime
    updated_at: datetime
    last_sent: Optional[datetime]
    send_count: int

    model_config = {"from_attributes": True}
