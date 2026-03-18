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


class SendRCSRequest(BaseModel):
    contact_ids: List[int]
    message: str
    msg_type: str = "standalone"  # standalone, card, carousel
    title: str = ""
    image_url: str = ""
    buttons: Optional[List[Dict]] = None
    cards: Optional[List[Dict]] = None
    fallback_type: str = "sms"


class SendBrandtalkRequest(BaseModel):
    contact_ids: List[int]
    message: str
    bubble_type: str = "TEXT"  # TEXT, IMAGE, WIDE, WIDE_ITEM_LIST, CAROUSEL_FEED, COMMERCE
    targeting: str = "I"  # M=전체, N=비친구, I=친구만
    buttons: Optional[List[Dict]] = None
    image_url: str = ""


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
