"""File management endpoints"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.models.auth import CognitoUser
from app.models.file import (
    FileCreate,
    FileListResponse,
    FileResponse,
    PresignedUrlResponse,
)
from app.models.license import LICENSE_TIERS
from app.services.dynamodb import db_service
from app.services.s3 import s3_service
from app.utils.auth import get_current_user

router = APIRouter()


def check_upload_limits(user_id: str, tier: str, file_size: int) -> None:
    """Check if user can upload based on their limits"""
    tier_config = LICENSE_TIERS.get(tier, LICENSE_TIERS["free"])

    # Check file size
    if file_size > tier_config["max_file_size_bytes"]:
        max_mb = tier_config["max_file_size_bytes"] / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size for {tier} tier is {max_mb:.0f}MB",
        )

    # Check storage limit
    current_storage = s3_service.get_user_storage_used(user_id)
    if current_storage + file_size > tier_config["storage_limit_bytes"]:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Storage limit exceeded. Please upgrade your plan or delete some files.",
        )

    # Check daily upload limit
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db_service.get_usage(user_id, today)
    uploads_today = usage.get("uploads_count", 0) if usage else 0

    if tier_config["uploads_per_day"] > 0 and uploads_today >= tier_config["uploads_per_day"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily upload limit reached ({tier_config['uploads_per_day']} uploads/day)",
        )


@router.post("/upload-url", response_model=PresignedUrlResponse)
async def get_upload_url(
    file_info: FileCreate,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get a presigned URL for file upload

    - Returns a URL that can be used to upload directly to S3
    - URL expires in 1 hour
    """
    # Check file type
    if file_info.content_type not in settings.allowed_file_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {settings.allowed_file_types}",
        )

    # Get user tier
    db_user = db_service.get_user(current_user.user_id)
    tier = db_user.get("license_tier", "free") if db_user else "free"

    # Check limits
    check_upload_limits(current_user.user_id, tier, file_info.size_bytes)

    # Generate S3 key and presigned URL
    s3_key = s3_service.generate_upload_key(current_user.user_id, file_info.filename)
    upload_data = s3_service.generate_presigned_upload_url(
        key=s3_key,
        content_type=file_info.content_type,
        expires_in=3600,
    )

    # Create file record in database
    file_record = db_service.create_file(
        user_id=current_user.user_id,
        filename=file_info.filename,
        content_type=file_info.content_type,
        size_bytes=file_info.size_bytes,
        s3_key=s3_key,
        encrypted=file_info.encrypted,
    )

    # Increment upload count
    today = datetime.utcnow().strftime("%Y-%m-%d")
    db_service.increment_usage(current_user.user_id, today, "uploads_count")

    return PresignedUrlResponse(
        url=upload_data["url"],
        expires_in=upload_data["expires_in"],
        file_id=file_record["file_id"],
    )


@router.post("/{file_id}/complete")
async def complete_upload(
    file_id: str,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Mark file upload as complete

    Call this after successfully uploading to the presigned URL
    """
    file_record = db_service.get_file(file_id, current_user.user_id)

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Verify file exists in S3
    if not s3_service.file_exists(file_record["s3_key"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not uploaded yet",
        )

    # Update file status
    updated = db_service.update_file_status(file_id, current_user.user_id, "ready")

    # Update user storage
    s3_metadata = s3_service.get_file_metadata(file_record["s3_key"])
    if s3_metadata:
        actual_size = s3_metadata.get("size_bytes", file_record["size_bytes"])
        db_user = db_service.get_user(current_user.user_id)
        current_storage = db_user.get("storage_used_bytes", 0) if db_user else 0
        db_service.update_user(
            current_user.user_id,
            {"storage_used_bytes": current_storage + actual_size},
        )

    return {"message": "Upload completed", "file_id": file_id}


@router.get("", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    List user's files with pagination
    """
    result = db_service.list_user_files(
        user_id=current_user.user_id,
        limit=page_size + 1,  # Get one extra to check if more exist
    )

    files = result["items"][:page_size]
    has_more = len(result["items"]) > page_size

    file_responses = [
        FileResponse(
            file_id=f["file_id"],
            filename=f["filename"],
            content_type=f["content_type"],
            size_bytes=f["size_bytes"],
            encrypted=f.get("encrypted", True),
            status=f["status"],
            created_at=f["created_at"],
        )
        for f in files
    ]

    return FileListResponse(
        files=file_responses,
        total_count=len(files),
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get file details
    """
    file_record = db_service.get_file(file_id, current_user.user_id)

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileResponse(
        file_id=file_record["file_id"],
        filename=file_record["filename"],
        content_type=file_record["content_type"],
        size_bytes=file_record["size_bytes"],
        encrypted=file_record.get("encrypted", True),
        status=file_record["status"],
        created_at=file_record["created_at"],
    )


@router.get("/{file_id}/download-url", response_model=PresignedUrlResponse)
async def get_download_url(
    file_id: str,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Get a presigned URL for file download

    - URL expires in 1 hour
    """
    file_record = db_service.get_file(file_id, current_user.user_id)

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if file_record["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not ready for download",
        )

    url = s3_service.generate_presigned_download_url(
        key=file_record["s3_key"],
        filename=file_record["filename"],
        expires_in=3600,
    )

    # Increment download count
    today = datetime.utcnow().strftime("%Y-%m-%d")
    db_service.increment_usage(current_user.user_id, today, "downloads_count")

    return PresignedUrlResponse(
        url=url,
        expires_in=3600,
        file_id=file_id,
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: CognitoUser = Depends(get_current_user),
):
    """
    Delete a file
    """
    file_record = db_service.get_file(file_id, current_user.user_id)

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Delete from S3
    s3_service.delete_file(file_record["s3_key"])

    # Delete from database
    db_service.delete_file(file_id, current_user.user_id)

    # Update user storage
    db_user = db_service.get_user(current_user.user_id)
    if db_user:
        current_storage = db_user.get("storage_used_bytes", 0)
        new_storage = max(0, current_storage - file_record["size_bytes"])
        db_service.update_user(current_user.user_id, {"storage_used_bytes": new_storage})

    return {"message": "File deleted", "file_id": file_id}
