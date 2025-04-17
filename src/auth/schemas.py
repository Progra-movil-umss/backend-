from pydantic import BaseModel, EmailStr, constr, field_validator, ConfigDict, model_validator
from typing import Optional, Union
from datetime import datetime
from uuid import UUID

from src.validators.password import validate_password

class UserBase(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)

class UserCreate(UserBase):
    password: constr(min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        is_valid, error_message = validate_password(v)
        if not is_valid:
            raise ValueError(error_message)
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[constr(min_length=3, max_length=50)] = None
    current_password: Optional[constr(min_length=8)] = None
    new_password: Optional[constr(min_length=8)] = None

    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        if v is not None:
            is_valid, error_message = validate_password(v)
            if not is_valid:
                raise ValueError(error_message)
        return v

class User(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: constr(min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        is_valid, error_message = validate_password(v)
        if not is_valid:
            raise ValueError(error_message)
        return v 