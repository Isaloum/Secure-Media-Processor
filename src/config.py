"""Configuration management for Secure Media Processor."""

import os
import tempfile
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

    def get_secure_temp_dir(self) -> Path:
        """Get or create a secure temporary directory with restricted permissions.

        Creates the temp directory with mode 0o700 (owner read/write/execute only)
        to prevent other users from accessing sensitive temporary files.

        Returns:
            Path to the secure temporary directory.
        """
        temp_dir = self.temp_path.resolve()

        if not temp_dir.exists():
            # Create directory with secure permissions (0o700 - owner only)
            temp_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
        else:
            # Ensure existing directory has secure permissions
            try:
                os.chmod(temp_dir, 0o700)
            except (OSError, PermissionError):
                # If we can't change permissions, log warning but continue
                pass

        return temp_dir

    def create_secure_temp_file(self, prefix: str = "smp_", suffix: str = ".tmp") -> Path:
        """Create a secure temporary file with restricted permissions.

        Creates a temp file with mode 0o600 (owner read/write only) in the
        configured temp directory.

        Args:
            prefix: Prefix for the temp file name.
            suffix: Suffix for the temp file name.

        Returns:
            Path to the created temporary file.
        """
        temp_dir = self.get_secure_temp_dir()

        # Create temp file with secure permissions
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=temp_dir)

        # Set restrictive permissions (owner read/write only)
        os.chmod(path, 0o600)

        # Close the file descriptor - caller will open as needed
        os.close(fd)

        return Path(path)


# Global settings instance
settings = Settings()