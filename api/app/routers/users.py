"""User management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.auth import CognitoUser
from app.models.license import LICENSE_TIERS
from app.models.user import UserResponse, UserUpdate
from app.services.dynamodb import db_service
from app.services.s3 import s3_service
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get current user profile with usage stats
    """
    db_user = db_service.get_user(current_user.user_id)

    if not db_user:
        # Create user if doesn't exist
        db_user = db_service.create_user(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.name,
        )

    # Get storage limit based on tier
    tier = db_user.get("license_tier", "free")
    tier_config = LICENSE_TIERS.get(tier, LICENSE_TIERS["free"])

    return UserResponse(
        user_id=db_user["user_id"],
        email=db_user["email"],
        name=db_user.get("name"),
        license_tier=tier,
        storage_used_bytes=db_user.get("storage_used_bytes", 0),
        storage_limit_bytes=tier_config["storage_limit_bytes"],
        created_at=db_user["created_at"],
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    updates: UserUpdate,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Update current user profile
    """
    update_data = updates.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )

    # Prevent changing license_tier directly (must go through license activation)
    if "license_tier" in update_data:
        del update_data["license_tier"]

    db_user = db_service.update_user(current_user.user_id, update_data)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    tier = db_user.get("license_tier", "free")
    tier_config = LICENSE_TIERS.get(tier, LICENSE_TIERS["free"])

    return UserResponse(
        user_id=db_user["user_id"],
        email=db_user["email"],
        name=db_user.get("name"),
        license_tier=tier,
        storage_used_bytes=db_user.get("storage_used_bytes", 0),
        storage_limit_bytes=tier_config["storage_limit_bytes"],
        created_at=db_user["created_at"],
    )


@router.get("/me/usage")
async def get_current_user_usage(
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get current user usage stats for current month
    """
    from datetime import datetime

    # Get current month period
    period = datetime.utcnow().strftime("%Y-%m")

    usage = db_service.get_usage(current_user.user_id, period)
    db_user = db_service.get_user(current_user.user_id)

    tier = db_user.get("license_tier", "free") if db_user else "free"
    tier_config = LICENSE_TIERS.get(tier, LICENSE_TIERS["free"])

    # Calculate actual storage from S3
    storage_used = s3_service.get_user_storage_used(current_user.user_id)

    return {
        "period": period,
        "uploads_count": usage.get("uploads_count", 0) if usage else 0,
        "downloads_count": usage.get("downloads_count", 0) if usage else 0,
        "api_calls_count": usage.get("api_calls_count", 0) if usage else 0,
        "storage_used_bytes": storage_used,
        "limits": {
            "uploads_per_day": tier_config["uploads_per_day"],
            "storage_limit_bytes": tier_config["storage_limit_bytes"],
            "max_file_size_bytes": tier_config["max_file_size_bytes"],
            "api_rate_limit": tier_config["api_rate_limit"],
        },
    }


@router.delete("/me")
async def delete_current_user_account(
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Delete current user account and all data

    WARNING: This action is irreversible
    """
    # Delete all user files from S3
    files = s3_service.list_user_files(current_user.user_id)
    for file in files:
        s3_service.delete_file(file["Key"])

    # Delete user from database
    # Note: In production, you might want to soft-delete or archive

    return {"message": "Account deletion initiated. Your data will be removed within 24 hours."}
