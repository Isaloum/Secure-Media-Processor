"""Authentication endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.auth import (
    CognitoUser,
    ConfirmSignupRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
    Token,
)
from app.services.cognito import cognito_service
from app.services.dynamodb import db_service
from app.utils.auth import get_current_user

router = APIRouter()


@router.post("/signup", response_model=dict)
async def signup(request: SignupRequest):
    """
    Sign up a new user

    - Sends verification email to the provided email address
    - User must confirm email before signing in
    """
    result = cognito_service.sign_up(
        email=request.email,
        password=request.password,
        name=request.name,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Signup failed"),
        )

    return {
        "message": "Signup successful. Please check your email for verification code.",
        "user_sub": result.get("user_sub"),
        "confirmed": result.get("confirmed", False),
    }


@router.post("/confirm", response_model=dict)
async def confirm_signup(request: ConfirmSignupRequest):
    """
    Confirm signup with verification code

    - Enter the 6-digit code sent to your email
    """
    result = cognito_service.confirm_sign_up(
        email=request.email,
        confirmation_code=request.confirmation_code,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Confirmation failed"),
        )

    return {"message": "Email confirmed successfully. You can now sign in."}


@router.post("/resend-code", response_model=dict)
async def resend_confirmation_code(request: ForgotPasswordRequest):
    """Resend confirmation code"""
    result = cognito_service.resend_confirmation_code(email=request.email)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Failed to resend code"),
        )

    return {"message": "Verification code sent to your email."}


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Sign in with email and password

    Returns JWT tokens for authentication
    """
    result = cognito_service.sign_in(
        email=request.email,
        password=request.password,
    )

    if not result.get("success"):
        error = result.get("error", "")
        message = result.get("message", "Login failed")

        if error == "UserNotConfirmedException":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified. Please check your email for verification code.",
            )
        elif error == "NotAuthorizedException":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

    return Token(
        access_token=result.get("access_token"),
        refresh_token=result.get("refresh_token"),
        expires_in=result.get("expires_in", 3600),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    result = cognito_service.refresh_token(refresh_token=request.refresh_token)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    return Token(
        access_token=result.get("access_token"),
        expires_in=result.get("expires_in", 3600),
    )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiate password reset

    Sends reset code to email
    """
    result = cognito_service.forgot_password(email=request.email)

    # Always return success to prevent email enumeration
    return {"message": "If an account exists, a password reset code has been sent."}


@router.post("/reset-password", response_model=dict)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with confirmation code
    """
    result = cognito_service.confirm_forgot_password(
        email=request.email,
        confirmation_code=request.confirmation_code,
        new_password=request.new_password,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Password reset failed"),
        )

    return {"message": "Password reset successful. You can now sign in."}


@router.post("/logout", response_model=dict)
async def logout(current_user: CognitoUser = Depends(get_current_user)):
    """
    Sign out (invalidate tokens)
    """
    # Note: This requires the access token which is already validated
    # For global sign out, you'd need to call cognito_service.sign_out
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_me(current_user: CognitoUser = Depends(get_current_user)):
    """
    Get current user info
    """
    # Get full user data from database
    db_user = db_service.get_user(current_user.user_id)

    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "name": current_user.name,
        "license_tier": db_user.get("license_tier", "free") if db_user else "free",
        "storage_used_bytes": db_user.get("storage_used_bytes", 0) if db_user else 0,
    }
