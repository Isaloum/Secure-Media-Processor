"""Authentication utilities and dependencies"""

import json
from functools import lru_cache
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.models.auth import CognitoUser
from app.services.dynamodb import db_service

# Security scheme
security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_cognito_jwks() -> dict:
    """
    Fetch and cache Cognito JWKS (JSON Web Key Set)
    Used to verify JWT tokens
    """
    try:
        response = httpx.get(settings.cognito_jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Return empty keys on error - tokens will fail validation
        return {"keys": []}


def get_public_key(token: str, jwks: dict) -> Optional[dict]:
    """Get the public key for a token from JWKS"""
    try:
        # Get key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            return None

        # Find matching key
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        return None
    except JWTError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a Cognito JWT token"""
    jwks = get_cognito_jwks()
    public_key = get_public_key(token, jwks)

    if not public_key:
        return None

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.cognito_issuer,
            options={"verify_exp": True},
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CognitoUser:
    """
    Dependency to get the current authenticated user
    Raises 401 if not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info from token
    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database (or create if first login)
    db_user = db_service.get_user(user_id)
    if not db_user:
        # First login - create user in database
        db_user = db_service.create_user(
            user_id=user_id,
            email=email,
            name=payload.get("name"),
        )

    return CognitoUser(
        user_id=user_id,
        email=email,
        email_verified=payload.get("email_verified", False),
        name=payload.get("name"),
        license_tier=db_user.get("license_tier", "free"),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CognitoUser]:
    """
    Dependency to get the current user if authenticated
    Returns None if not authenticated (doesn't raise error)
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
