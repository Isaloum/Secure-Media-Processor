"""License models"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LicenseBase(BaseModel):
    """Base license model"""
    tier: str = "free"  # free, pro, enterprise


class LicenseCreate(BaseModel):
    """License activation request"""
    license_key: str
    email: Optional[str] = None


class License(LicenseBase):
    """License model stored in DynamoDB"""
    license_key: str
    user_id: Optional[str] = None
    gumroad_sale_id: Optional[str] = None
    gumroad_product_id: Optional[str] = None
    status: str = "active"  # active, expired, revoked
    activations: int = 0
    max_activations: int = 3
    created_at: str
    expires_at: Optional[str] = None

    class Config:
        from_attributes = True


class LicenseResponse(BaseModel):
    """License response model"""
    license_key: str
    tier: str
    status: str
    activations: int
    max_activations: int
    expires_at: Optional[str] = None
    features: dict = {}


class LicenseValidation(BaseModel):
    """License validation response"""
    valid: bool
    tier: str = "free"
    message: str = ""
    features: dict = {}


# License tier configurations
LICENSE_TIERS = {
    "free": {
        "storage_limit_bytes": 100 * 1024 * 1024,  # 100MB
        "uploads_per_day": 10,
        "max_file_size_bytes": 10 * 1024 * 1024,  # 10MB
        "gpu_processing": False,
        "api_rate_limit": 60,  # requests per minute
        "cloud_connectors": ["local"],
    },
    "pro": {
        "storage_limit_bytes": 10 * 1024 * 1024 * 1024,  # 10GB
        "uploads_per_day": 500,
        "max_file_size_bytes": 500 * 1024 * 1024,  # 500MB
        "gpu_processing": True,
        "api_rate_limit": 300,
        "cloud_connectors": ["local", "s3", "gdrive", "dropbox"],
    },
    "enterprise": {
        "storage_limit_bytes": 100 * 1024 * 1024 * 1024,  # 100GB
        "uploads_per_day": -1,  # Unlimited
        "max_file_size_bytes": 5 * 1024 * 1024 * 1024,  # 5GB
        "gpu_processing": True,
        "api_rate_limit": 1000,
        "cloud_connectors": ["local", "s3", "gdrive", "dropbox"],
    },
}
