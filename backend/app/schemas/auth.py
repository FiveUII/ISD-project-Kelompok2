"""
Pydantic v2 schemas for the auth endpoints.
Kept minimal — only what the API sends/receives.
"""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str  # min 8 chars enforced in auth_service
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_email_verified: bool

    model_config = {"from_attributes": True}
