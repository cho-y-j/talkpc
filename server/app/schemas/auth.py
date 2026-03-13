from typing import Optional
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    phone: str = ""
    email: str = ""
    device_id: str = ""
    device_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: str = ""
    device_name: str = ""


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class DeviceVerifyRequest(BaseModel):
    username: str
    device_id: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    """로그인 응답 - 기기 인증 필요 여부 포함"""
    requires_verify: bool = False
    verify_method: str = ""  # email, admin
    message: str = ""
    access_token: str = ""
    token_type: str = "bearer"
    user_id: int = 0
    username: str = ""
    name: str = ""
    role: str = ""
