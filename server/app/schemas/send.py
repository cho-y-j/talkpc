from typing import Dict, List, Optional
from pydantic import BaseModel


class SendSMSRequest(BaseModel):
    contact_ids: List[int]
    message: str
    subject: str = "알림"


class SendAlimtalkRequest(BaseModel):
    contact_ids: List[int]
    message: str
    template_code: str = ""
    buttons: Optional[List[Dict]] = None
    fallback_type: str = "sms"


class SendResultResponse(BaseModel):
    mseq: int
    status: str
    detail: str = ""


class BatchSendResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[Dict]
    total_cost: int
