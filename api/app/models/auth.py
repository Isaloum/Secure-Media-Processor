"""Authentication models"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    """JWT Token payload"""
    sub: str  # user_id (Cognito sub)
    email: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    iss: Optional[str] = None


class CognitoUser(BaseModel):
    """User data from Cognito token"""
    user_id: str  # Cognito sub
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    license_tier: Optional[str] = "free"


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Signup request"""
    email: EmailStr
    password: str
    name: Optional[str] = None


class ConfirmSignupRequest(BaseModel):
    """Confirm signup with verification code"""
    email: EmailStr
    confirmation_code: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with confirmation code"""
    email: EmailStr
    confirmation_code: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
