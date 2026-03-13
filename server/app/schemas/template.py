from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    category: str = "all"
    contents: List[str] = []
    image_path: str = ""


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    contents: Optional[List[str]] = None
    image_path: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    contents: list
    image_path: str
    created_at: datetime

    model_config = {"from_attributes": True}
