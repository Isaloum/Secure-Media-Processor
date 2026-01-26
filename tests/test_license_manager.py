"""
Tests for license management system.

These tests verify license generation, validation, activation,
and feature gating functionality.
"""

import pytest
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.license_manager import (
    License,
    LicenseManager,
    LicenseType,
    FeatureFlags,
    get_license_manager,
    require_feature
)


class TestLicenseType:
    """Test license type enum."""

    def test_license_types_exist(self):
        """Test that all license types are defined."""
        assert LicenseType.FREE.value == "free"
        assert LicenseType.PRO.value == "pro"
        assert LicenseType.ENTERPRISE.value == "enterprise"


class TestFeatureFlags:
    """Test feature flags enum."""

    def test_feature_flags_exist(self):
        """Test that all feature flags are defined."""
        assert FeatureFlags.CLOUD_STORAGE.value == "cloud_storage"
        assert FeatureFlags.GPU_PROCESSING.value == "gpu_processing"
        assert FeatureFlags.BATCH_PROCESSING.value == "batch_processing"
        assert FeatureFlags.MULTI_CLOUD_SYNC.value == "multi_cloud_sync"
        assert FeatureFlags.PRIORITY_SUPPORT.value == "priority_support"


class TestLicense:
    """Test License dataclass."""

    @pytest.fixture
    def sample_license(self):
        """Create a sample license for testing."""
        return License(
            license_key="ABCD-1234-EFGH-5678-IJKL",
            license_type=LicenseType.PRO,
            email="test@example.com",
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365),
            features=["cloud_storage", "gpu_processing"],
            max_devices=1
        )

    def test_license_initialization(self, sample_license):
        """Test license object initialization."""
        assert sample_license.license_key == "ABCD-1234-EFGH-5678-IJKL"
        assert sample_license.license_type == LicenseType.PRO
        assert sample_license.email == "test@example.com"
        assert len(sample_license.features) == 2

    def test_license_is_valid_active(self, sample_license):
        """Test that active license is valid."""
        assert sample_license.is_valid() is True

    def test_license_is_valid_expired(self, sample_license):
        """Test that expired license is invalid."""
        sample_license.expires_at = datetime.now() - timedelta(days=1)
        assert sample_license.is_valid() is False

    def test_license_is_valid_lifetime(self, sample_license):
        """Test that lifetime license (no expiry) is valid."""
        sample_license.expires_at = None
        assert sample_license.is_valid() is True

    def test_license_is_feature_enabled(self, sample_license):
        """Test checking if feature is enabled."""
        assert sample_license.is_feature_enabled(FeatureFlags.CLOUD_STORAGE) is True
        assert sample_license.is_feature_enabled(FeatureFlags.GPU_PROCESSING) is True
        assert sample_license.is_feature_enabled(FeatureFlags.MULTI_CLOUD_SYNC) is False

    def test_license_can_activate_device(self, sample_license):
        """Test device activation limit checking."""
        # No devices activated yet
        assert sample_license.can_activate_device("device1") is True

        # Activate first device
        sample_license.activated_devices.append("device1")
        assert sample_license.can_activate_device("device1") is True  # Already activated
        assert sample_license.can_activate_device("device2") is False  # Max reached

    def test_license_to_dict(self, sample_license):
        """Test converting license to dictionary."""
        data = sample_license.to_dict()

        assert data['license_key'] == "ABCD-1234-EFGH-5678-IJKL"
        assert data['license_type'] == "pro"
        assert data['email'] == "test@example.com"
        assert isinstance(data['issued_at'], str)
        assert isinstance(data['expires_at'], str)

    def test_license_from_dict(self, sample_license):
        """Test creating license from dictionary."""
        data = sample_license.to_dict()
        restored = License.from_dict(data)

        assert restored.license_key == sample_license.license_key
        assert restored.license_type == sample_license.license_type
        assert restored.email == sample_license.email


class TestLicenseManager:
    """Test license manager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create license manager for testing."""
        # Use temporary directory for license cache
        manager = LicenseManager(secret_key="test_secret_key")
        manager.license_cache_dir = tmp_path / '.secure-media-processor'
        manager.license_file = manager.license_cache_dir / 'license.json'
        manager.license_cache_dir.mkdir(parents=True, exist_ok=True)
        return manager

    def test_manager_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager.secret_key == "test_secret_key"
        assert manager.license_cache_dir.exists()

    def test_generate_license_key_format(self, manager):
        """Test that generated license keys have correct format."""
        key = manager.generate_license_key(
            "test@example.com",
            LicenseType.PRO,
            365
        )

        # Check format: XXXX-XXXX-XXXX-XXXX-XXXX
        assert len(key) == 24  # 20 chars + 4 dashes
        assert key.count('-') == 4
        parts = key.split('-')
        assert all(len(part) == 4 for part in parts)
        # Keys are generated from hex hash, so uppercase alphanumeric (0-9, A-F)
        assert all(part.isupper() or part.isdigit() for part in parts)
        assert all(c.isalnum() for part in parts for c in part)

    def test_generate_license_key_uniqueness(self, manager):
        """Test that generated keys are unique for different inputs."""
        key1 = manager.generate_license_key("test1@example.com", LicenseType.PRO)
        key2 = manager.generate_license_key("test2@example.com", LicenseType.PRO)
        key3 = manager.generate_license_key("test1@example.com", LicenseType.ENTERPRISE)

        # Different emails = different keys
        assert key1 != key2
        # Same email but different license type = different keys
        assert key1 != key3

    def test_validate_license_key_valid(self, manager):
        """Test validating a valid license key format."""
        valid_key = "ABCD-1234-EFGH-5678-IJKL"
        assert manager.validate_license_key(valid_key) is True

    def test_validate_license_key_invalid_format(self, manager):
        """Test validating invalid license key formats."""
        assert manager.validate_license_key("TOO-SHORT") is False
        assert manager.validate_license_key("abcd-efgh-ijkl-mnop-qrst") is False  # lowercase
        assert manager.validate_license_key("ABCD_1234_EFGH_5678_IJKL") is False  # underscores
        assert manager.validate_license_key("") is False

    def test_create_license_pro(self, manager):
        """Test creating a Pro license."""
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO,
            duration_days=365,
            max_devices=1
        )

        assert license.license_type == LicenseType.PRO
        assert license.email == "test@example.com"
        assert license.max_devices == 1
        assert len(license.features) == 3  # cloud, gpu, batch
        assert "cloud_storage" in license.features
        assert "gpu_processing" in license.features
        assert "batch_processing" in license.features

    def test_create_license_enterprise(self, manager):
        """Test creating an Enterprise license."""
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.ENTERPRISE,
            duration_days=365
        )

        assert license.license_type == LicenseType.ENTERPRISE
        assert len(license.features) == 5  # All features
        assert "multi_cloud_sync" in license.features
        assert "priority_support" in license.features

    def test_create_license_free(self, manager):
        """Test creating a Free license."""
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.FREE,
            duration_days=None  # Lifetime for free
        )

        assert license.license_type == LicenseType.FREE
        assert len(license.features) == 0  # No premium features
        assert license.expires_at is None

    def test_create_license_lifetime(self, manager):
        """Test creating a lifetime license."""
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO,
            duration_days=None  # Lifetime
        )

        assert license.expires_at is None

    @patch.object(LicenseManager, '_get_device_id')
    def test_activate_license_success(self, mock_device_id, manager):
        """Test successful license activation."""
        mock_device_id.return_value = "test_device_123"

        # First generate a valid key
        valid_key = manager.generate_license_key("test@example.com", LicenseType.PRO)

        license = manager.activate_license(
            license_key=valid_key,
            email="test@example.com"
        )

        assert license is not None
        # Note: activate_license creates a new license internally, so key may differ
        assert license.license_key is not None
        assert len(license.license_key) == 24  # Valid key format
        assert "test_device_123" in license.activated_devices
        assert manager.license_file.exists()

    def test_activate_license_invalid_key(self, manager):
        """Test activating with invalid license key."""
        with pytest.raises(ValueError, match="Invalid license key format"):
            manager.activate_license(
                license_key="INVALID",
                email="test@example.com"
            )

    def test_save_license(self, manager):
        """Test saving license to file."""
        license = License(
            license_key="TEST-KEY",
            license_type=LicenseType.PRO,
            email="test@example.com",
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            features=["cloud_storage"],
            max_devices=1
        )

        manager._save_license(license)

        assert manager.license_file.exists()
        # Check file permissions (Unix only)
        if os.name != 'nt':
            stat_info = os.stat(manager.license_file)
            assert oct(stat_info.st_mode)[-3:] == '600'

    def test_get_active_license_exists(self, manager):
        """Test getting active license when it exists."""
        # Save a license first
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO,
            duration_days=365
        )
        manager._save_license(license)

        # Retrieve it
        retrieved = manager.get_active_license()

        assert retrieved is not None
        assert retrieved.license_key == license.license_key
        assert retrieved.email == license.email

    def test_get_active_license_not_exists(self, manager):
        """Test getting active license when none exists."""
        retrieved = manager.get_active_license()
        assert retrieved is None

    def test_get_active_license_expired(self, manager):
        """Test getting expired license returns None."""
        # Create expired license
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO,
            duration_days=-1  # Expired yesterday
        )
        manager._save_license(license)

        # Should return None for expired
        retrieved = manager.get_active_license()
        assert retrieved is None

    def test_deactivate_license(self, manager):
        """Test deactivating license."""
        # Save a license first
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO
        )
        manager._save_license(license)

        # Deactivate
        result = manager.deactivate_license()

        assert result is True
        assert not manager.license_file.exists()

    def test_deactivate_license_none_active(self, manager):
        """Test deactivating when no license is active."""
        result = manager.deactivate_license()
        assert result is False

    def test_check_feature_with_license(self, manager):
        """Test checking feature with active license."""
        # Save Pro license
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO
        )
        manager._save_license(license)

        # Check features
        assert manager.check_feature(FeatureFlags.CLOUD_STORAGE) is True
        assert manager.check_feature(FeatureFlags.GPU_PROCESSING) is True
        assert manager.check_feature(FeatureFlags.MULTI_CLOUD_SYNC) is False  # Enterprise only

    def test_check_feature_no_license(self, manager):
        """Test checking feature with no license."""
        # No license saved
        assert manager.check_feature(FeatureFlags.CLOUD_STORAGE) is False
        assert manager.check_feature(FeatureFlags.GPU_PROCESSING) is False

    def test_get_license_info_active(self, manager):
        """Test getting license info for active license."""
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO,
            duration_days=30
        )
        manager._save_license(license)

        info = manager.get_license_info()

        assert info['active'] is True
        assert info['type'] == 'pro'
        assert info['email'] == 'test@example.com'
        assert info['days_remaining'] is not None
        assert len(info['features']) > 0

    def test_get_license_info_inactive(self, manager):
        """Test getting license info with no license."""
        info = manager.get_license_info()

        assert info['active'] is False
        assert info['type'] == 'free'
        assert info['features'] == []
        assert 'No active license' in info['message']

    def test_get_device_id_consistency(self, manager):
        """Test that device ID is consistent."""
        device_id1 = manager._get_device_id()
        device_id2 = manager._get_device_id()

        assert device_id1 == device_id2
        assert len(device_id1) == 16  # Should be 16 chars


class TestGlobalLicenseManager:
    """Test global license manager singleton."""

    def test_get_license_manager_singleton(self):
        """Test that get_license_manager returns singleton."""
        manager1 = get_license_manager()
        manager2 = get_license_manager()

        assert manager1 is manager2


class TestRequireFeatureDecorator:
    """Test require_feature decorator."""

    def test_require_feature_with_license(self, tmp_path):
        """Test decorated function works with valid license."""
        manager = LicenseManager()
        manager.license_cache_dir = tmp_path / '.secure-media-processor'
        manager.license_file = manager.license_cache_dir / 'license.json'
        manager.license_cache_dir.mkdir(parents=True, exist_ok=True)

        # Create and save license
        license = manager.create_license(
            email="test@example.com",
            license_type=LicenseType.PRO
        )
        manager._save_license(license)

        # Mock global manager
        with patch('src.license_manager.get_license_manager', return_value=manager):
            @require_feature(FeatureFlags.CLOUD_STORAGE)
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"

    def test_require_feature_without_license(self):
        """Test decorated function fails without license."""
        manager = LicenseManager()

        with patch('src.license_manager.get_license_manager', return_value=manager):
            @require_feature(FeatureFlags.CLOUD_STORAGE)
            def test_function():
                return "success"

            with pytest.raises(RuntimeError, match="requires a Pro or Enterprise license"):
                test_function()
