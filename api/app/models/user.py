"""User models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """User creation request"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update request"""
    name: Optional[str] = None
    license_tier: Optional[str] = None


class User(UserBase):
    """User model stored in DynamoDB"""
    user_id: str
    license_tier: str = "free"
    storage_used_bytes: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    email: EmailStr
    name: Optional[str] = None
    license_tier: str = "free"
    storage_used_bytes: int = 0
    storage_limit_bytes: int = 104857600  # 100MB for free tier
    created_at: str
