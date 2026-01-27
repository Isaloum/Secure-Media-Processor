"""License management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.auth import CognitoUser
from app.models.license import (
    LICENSE_TIERS,
    LicenseCreate,
    LicenseResponse,
    LicenseValidation,
)
from app.services.dynamodb import db_service
from app.services.gumroad import gumroad_service
from app.utils.auth import get_current_user

router = APIRouter()


@router.post("/activate", response_model=LicenseResponse)
async def activate_license(
    license_data: LicenseCreate,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Activate a license key for the current user

    - Validates the license with Gumroad
    - Associates the license with your account
    - Upgrades your account tier
    """
    license_key = license_data.license_key.strip()

    # Check if license already exists in our database
    existing_license = db_service.get_license(license_key)

    if existing_license:
        # License already activated
        if existing_license.get("user_id") == current_user.user_id:
            # Already activated by this user
            return LicenseResponse(
                license_key=license_key,
                tier=existing_license["tier"],
                status=existing_license["status"],
                activations=existing_license.get("activations", 1),
                max_activations=existing_license.get("max_activations", 3),
                features=LICENSE_TIERS.get(existing_license["tier"], {}),
            )
        elif existing_license.get("activations", 0) >= existing_license.get("max_activations", 3):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License has reached maximum activations",
            )

    # Verify license with Gumroad
    verification = await gumroad_service.verify_license(
        license_key=license_key,
        increment_uses=True,
    )

    if not verification.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification.get("message", "Invalid license key"),
        )

    # Check for refunded/disputed
    if verification.get("refunded") or verification.get("disputed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This license has been refunded or disputed",
        )

    tier = verification.get("tier", "pro")

    # Create or update license in database
    if existing_license:
        # Activate for additional user
        activated = db_service.activate_license(license_key, current_user.user_id)
        if not activated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to activate license",
            )
        license_record = activated
    else:
        # Create new license
        license_record = db_service.create_license(
            license_key=license_key,
            tier=tier,
            gumroad_sale_id=verification.get("sale_id"),
            max_activations=3,
        )
        # Activate for current user
        db_service.activate_license(license_key, current_user.user_id)

    # Update user's license tier
    db_service.update_user(current_user.user_id, {"license_tier": tier})

    return LicenseResponse(
        license_key=license_key,
        tier=tier,
        status="active",
        activations=license_record.get("activations", 1),
        max_activations=license_record.get("max_activations", 3),
        features=LICENSE_TIERS.get(tier, {}),
    )


@router.post("/validate", response_model=LicenseValidation)
async def validate_license(license_data: LicenseCreate):
    """
    Validate a license key (without activating)

    - Checks if the license is valid
    - Returns tier and features
    - Does not require authentication
    """
    license_key = license_data.license_key.strip()

    # Check local database first
    existing_license = db_service.get_license(license_key)

    if existing_license and existing_license.get("status") == "active":
        tier = existing_license.get("tier", "pro")
        return LicenseValidation(
            valid=True,
            tier=tier,
            message="License is valid",
            features=LICENSE_TIERS.get(tier, {}),
        )

    # Verify with Gumroad (without incrementing uses)
    verification = await gumroad_service.verify_license(
        license_key=license_key,
        increment_uses=False,
    )

    if not verification.get("valid"):
        return LicenseValidation(
            valid=False,
            tier="free",
            message=verification.get("message", "Invalid license key"),
            features=LICENSE_TIERS.get("free", {}),
        )

    tier = verification.get("tier", "pro")
    return LicenseValidation(
        valid=True,
        tier=tier,
        message="License is valid",
        features=LICENSE_TIERS.get(tier, {}),
    )


@router.get("/current", response_model=LicenseResponse)
async def get_current_license(
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get current user's license information
    """
    db_user = db_service.get_user(current_user.user_id)
    tier = db_user.get("license_tier", "free") if db_user else "free"

    # For free tier, return basic info
    if tier == "free":
        return LicenseResponse(
            license_key="",
            tier="free",
            status="active",
            activations=0,
            max_activations=0,
            features=LICENSE_TIERS.get("free", {}),
        )

    # Find user's license
    # Note: In production, you'd want to store license_key on user record
    # For now, return tier-based response
    return LicenseResponse(
        license_key="[activated]",
        tier=tier,
        status="active",
        activations=1,
        max_activations=3,
        features=LICENSE_TIERS.get(tier, {}),
    )


@router.get("/tiers")
async def get_license_tiers():
    """
    Get available license tiers and their features
    """
    return {
        "tiers": {
            name: {
                "name": name.title(),
                "storage_limit_gb": config["storage_limit_bytes"] / (1024 ** 3),
                "uploads_per_day": config["uploads_per_day"],
                "max_file_size_mb": config["max_file_size_bytes"] / (1024 ** 2),
                "gpu_processing": config["gpu_processing"],
                "api_rate_limit": config["api_rate_limit"],
                "cloud_connectors": config["cloud_connectors"],
            }
            for name, config in LICENSE_TIERS.items()
        }
    }


@router.delete("/deactivate")
async def deactivate_license(
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Deactivate license and downgrade to free tier
    """
    db_user = db_service.get_user(current_user.user_id)

    if not db_user or db_user.get("license_tier") == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active license to deactivate",
        )

    # Downgrade to free tier
    db_service.update_user(current_user.user_id, {"license_tier": "free"})

    return {"message": "License deactivated. Your account has been downgraded to free tier."}
