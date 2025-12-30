"""Configuration management for Secure Media Processor."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_bucket_name: Optional[str] = None
    
    # GCP Configuration
    gcp_project_id: Optional[str] = None
    gcp_bucket_name: Optional[str] = None
    gcp_credentials_path: Optional[Path] = None
    
    # Azure Configuration
    azure_connection_string: Optional[str] = None
    azure_container_name: Optional[str] = None
    
    # Encryption
    master_key_path: Path = Field(default=Path("./keys/master.key"))
    encryption_algorithm: str = "AES-256-GCM"
    
    # Processing
    gpu_enabled: bool = True
    batch_size: int = 32
    max_workers: int = 4
    
    # Storage
    local_storage_path: Path = Field(default=Path("./media_storage"))
    temp_path: Path = Field(default=Path("./temp"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()