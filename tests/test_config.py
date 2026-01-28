"""Tests for configuration management module."""

import os
import stat
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config import Settings, settings


class TestSettingsDefaults:
    """Test Settings class default values."""

    def test_default_aws_region(self):
        """Test default AWS region."""
        s = Settings()
        assert s.aws_region == "us-east-1"

    def test_default_aws_credentials_none(self):
        """Test AWS credentials default to None."""
        s = Settings()
        assert s.aws_access_key_id is None
        assert s.aws_secret_access_key is None
        assert s.aws_bucket_name is None

    def test_default_gcp_config_none(self):
        """Test GCP config defaults to None."""
        s = Settings()
        assert s.gcp_project_id is None
        assert s.gcp_bucket_name is None
        assert s.gcp_credentials_path is None

    def test_default_encryption_settings(self):
        """Test encryption defaults."""
        s = Settings()
        assert s.master_key_path == Path("./keys/master.key")
        assert s.encryption_algorithm == "AES-256-GCM"

    def test_default_processing_settings(self):
        """Test processing defaults."""
        s = Settings()
        assert s.gpu_enabled is True
        assert s.batch_size == 32
        assert s.max_workers == 4

    def test_default_storage_paths(self):
        """Test storage path defaults."""
        s = Settings()
        assert s.local_storage_path == Path("./media_storage")
        assert s.temp_path == Path("./temp")


class TestSettingsEnvironment:
    """Test Settings loading from environment variables."""

    def test_load_aws_credentials_from_env(self, monkeypatch):
        """Test loading AWS credentials from environment."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.setenv("AWS_BUCKET_NAME", "test-bucket")

        s = Settings()
        assert s.aws_access_key_id == "test-access-key"
        assert s.aws_secret_access_key == "test-secret-key"
        assert s.aws_region == "eu-west-1"
        assert s.aws_bucket_name == "test-bucket"

    def test_load_gcp_config_from_env(self, monkeypatch):
        """Test loading GCP config from environment."""
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GCP_BUCKET_NAME", "test-gcp-bucket")

        s = Settings()
        assert s.gcp_project_id == "test-project"
        assert s.gcp_bucket_name == "test-gcp-bucket"

    def test_load_processing_settings_from_env(self, monkeypatch):
        """Test loading processing settings from environment."""
        monkeypatch.setenv("GPU_ENABLED", "false")
        monkeypatch.setenv("BATCH_SIZE", "64")
        monkeypatch.setenv("MAX_WORKERS", "8")

        s = Settings()
        assert s.gpu_enabled is False
        assert s.batch_size == 64
        assert s.max_workers == 8

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test that environment variables are case insensitive."""
        monkeypatch.setenv("aws_region", "ap-south-1")

        s = Settings()
        assert s.aws_region == "ap-south-1"


class TestSecureTempDir:
    """Test secure temporary directory functionality."""

    def test_get_secure_temp_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that get_secure_temp_dir creates the directory."""
        temp_dir = tmp_path / "secure_temp"
        monkeypatch.setenv("TEMP_PATH", str(temp_dir))

        s = Settings()
        s.temp_path = temp_dir

        result = s.get_secure_temp_dir()

        assert result.exists()
        assert result.is_dir()

    def test_get_secure_temp_dir_sets_permissions(self, tmp_path, monkeypatch):
        """Test that directory has secure permissions (0o700)."""
        temp_dir = tmp_path / "secure_temp"
        monkeypatch.setenv("TEMP_PATH", str(temp_dir))

        s = Settings()
        s.temp_path = temp_dir

        result = s.get_secure_temp_dir()

        # Check permissions (owner read/write/execute only)
        mode = result.stat().st_mode
        assert mode & 0o777 == 0o700

    def test_get_secure_temp_dir_existing_directory(self, tmp_path):
        """Test behavior with existing directory."""
        temp_dir = tmp_path / "existing_temp"
        temp_dir.mkdir(mode=0o755)  # Less secure permissions

        s = Settings()
        s.temp_path = temp_dir

        result = s.get_secure_temp_dir()

        assert result.exists()
        # Should update permissions to 0o700
        mode = result.stat().st_mode
        assert mode & 0o777 == 0o700

    def test_get_secure_temp_dir_returns_resolved_path(self, tmp_path):
        """Test that returned path is resolved (absolute)."""
        temp_dir = tmp_path / "relative" / ".." / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.get_secure_temp_dir()

        assert result.is_absolute()
        assert ".." not in str(result)


class TestSecureTempFile:
    """Test secure temporary file functionality."""

    def test_create_secure_temp_file_creates_file(self, tmp_path):
        """Test that create_secure_temp_file creates a file."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.create_secure_temp_file()

        assert result.exists()
        assert result.is_file()

    def test_create_secure_temp_file_sets_permissions(self, tmp_path):
        """Test that temp file has secure permissions (0o600)."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.create_secure_temp_file()

        # Check permissions (owner read/write only)
        mode = result.stat().st_mode
        assert mode & 0o777 == 0o600

    def test_create_secure_temp_file_custom_prefix(self, tmp_path):
        """Test custom prefix for temp file."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.create_secure_temp_file(prefix="custom_")

        assert result.name.startswith("custom_")

    def test_create_secure_temp_file_custom_suffix(self, tmp_path):
        """Test custom suffix for temp file."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.create_secure_temp_file(suffix=".enc")

        assert result.name.endswith(".enc")

    def test_create_secure_temp_file_in_secure_dir(self, tmp_path):
        """Test that temp file is created in secure directory."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        result = s.create_secure_temp_file()

        assert result.parent == temp_dir.resolve()

    def test_create_multiple_temp_files_unique(self, tmp_path):
        """Test that multiple temp files have unique names."""
        temp_dir = tmp_path / "temp"

        s = Settings()
        s.temp_path = temp_dir

        file1 = s.create_secure_temp_file()
        file2 = s.create_secure_temp_file()
        file3 = s.create_secure_temp_file()

        assert file1 != file2 != file3


class TestGlobalSettings:
    """Test global settings instance."""

    def test_global_settings_exists(self):
        """Test that global settings instance exists."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_global_settings_has_defaults(self):
        """Test that global settings has default values."""
        assert settings.aws_region == "us-east-1"
        assert settings.encryption_algorithm == "AES-256-GCM"
        assert settings.gpu_enabled is True


class TestSettingsValidation:
    """Test settings validation and edge cases."""

    def test_invalid_batch_size_type(self, monkeypatch):
        """Test that invalid batch size raises error."""
        monkeypatch.setenv("BATCH_SIZE", "not-a-number")

        with pytest.raises(Exception):
            Settings()

    def test_path_conversion(self, monkeypatch):
        """Test that string paths are converted to Path objects."""
        monkeypatch.setenv("MASTER_KEY_PATH", "/custom/key/path.key")

        s = Settings()
        assert isinstance(s.master_key_path, Path)
        assert s.master_key_path == Path("/custom/key/path.key")

    def test_boolean_conversion(self, monkeypatch):
        """Test various boolean string conversions."""
        # Test 'true'
        monkeypatch.setenv("GPU_ENABLED", "true")
        s = Settings()
        assert s.gpu_enabled is True

        # Test 'false'
        monkeypatch.setenv("GPU_ENABLED", "false")
        s = Settings()
        assert s.gpu_enabled is False

        # Test '1'
        monkeypatch.setenv("GPU_ENABLED", "1")
        s = Settings()
        assert s.gpu_enabled is True

        # Test '0'
        monkeypatch.setenv("GPU_ENABLED", "0")
        s = Settings()
        assert s.gpu_enabled is False
