"""File models"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FileBase(BaseModel):
    """Base file model"""
    filename: str
    content_type: str
    size_bytes: int


class FileCreate(BaseModel):
    """File upload request"""
    filename: str
    content_type: str
    size_bytes: int
    encrypted: bool = True


class File(FileBase):
    """File model stored in DynamoDB"""
    file_id: str
    user_id: str
    s3_key: str
    encrypted: bool = True
    checksum: Optional[str] = None
    status: str = "pending"  # pending, processing, ready, failed
    created_at: str
    updated_at: str
    expires_at: Optional[int] = None  # TTL timestamp

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    """File response model"""
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    encrypted: bool
    status: str
    created_at: str
    download_url: Optional[str] = None


class FileListResponse(BaseModel):
    """Paginated file list response"""
    files: List[FileResponse]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class PresignedUrlResponse(BaseModel):
    """Presigned URL for upload/download"""
    url: str
    fields: Optional[dict] = None  # For POST uploads
    expires_in: int = 3600
    file_id: Optional[str] = None
