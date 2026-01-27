"""
Application configuration using Pydantic Settings
Loads from environment variables (set by Lambda or .env file)
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Environment
    environment: str = "dev"
    debug: bool = False

    # AWS
    aws_region: str = "us-east-1"

    # DynamoDB Tables
    dynamodb_users_table: str = "secure-media-processor-prod-users"
    dynamodb_files_table: str = "secure-media-processor-prod-files"
    dynamodb_licenses_table: str = "secure-media-processor-prod-licenses"
    dynamodb_usage_table: str = "secure-media-processor-prod-usage"

    # S3
    s3_media_bucket: str = ""

    # Cognito
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_region: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Gumroad
    gumroad_api_key: Optional[str] = None
    gumroad_product_id: Optional[str] = None

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_uploads_per_day: int = 100

    # File Upload
    max_file_size_mb: int = 100
    allowed_file_types: str = "image/jpeg,image/png,image/webp,video/mp4,video/webm,audio/mp3,audio/wav"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from comma-separated string"""
        return [ft.strip() for ft in self.allowed_file_types.split(",") if ft.strip()]

    @property
    def cognito_issuer(self) -> str:
        """Cognito token issuer URL"""
        region = self.cognito_region or self.aws_region
        return f"https://cognito-idp.{region}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def cognito_jwks_url(self) -> str:
        """Cognito JWKS URL for token verification"""
        region = self.cognito_region or self.aws_region
        return f"https://cognito-idp.{region}.amazonaws.com/{self.cognito_user_pool_id}/.well-known/jwks.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
