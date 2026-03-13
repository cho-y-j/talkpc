from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    phone: str = ""
    email: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    name: str
    role: str
