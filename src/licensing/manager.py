"""
License management system for Secure Media Processor.

Implements license key generation, validation, and feature gating
for monetizing premium features.
"""

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum


class LicenseType(Enum):
    """License tier types."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class FeatureFlags(Enum):
    """Premium features that can be gated."""
    CLOUD_STORAGE = "cloud_storage"  # S3, Drive, Dropbox connectors
    GPU_PROCESSING = "gpu_processing"  # GPU-accelerated processing
    BATCH_PROCESSING = "batch_processing"  # Batch operations
    MULTI_CLOUD_SYNC = "multi_cloud_sync"  # Sync between clouds
    PRIORITY_SUPPORT = "priority_support"  # Email/chat support


@dataclass
class License:
    """License information."""
    license_key: str
    license_type: LicenseType
    email: str
    issued_at: datetime
    expires_at: Optional[datetime]
    features: List[str]
    max_devices: int = 1
    activated_devices: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize optional fields."""
        if self.activated_devices is None:
            self.activated_devices = []
        if self.metadata is None:
            self.metadata = {}

    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    def is_feature_enabled(self, feature: FeatureFlags) -> bool:
        """Check if a feature is enabled for this license."""
        return feature.value in self.features

    def can_activate_device(self, device_id: str) -> bool:
        """Check if a new device can be activated."""
        if device_id in self.activated_devices:
            return True  # Already activated
        return len(self.activated_devices) < self.max_devices

    def to_dict(self) -> Dict[str, Any]:
        """Convert license to dictionary."""
        data = asdict(self)
        data['license_type'] = self.license_type.value
        data['issued_at'] = self.issued_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat() if self.expires_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'License':
        """Create license from dictionary."""
        data['license_type'] = LicenseType(data['license_type'])
        data['issued_at'] = datetime.fromisoformat(data['issued_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class LicenseManager:
    """Manages license generation, validation, and activation."""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize license manager.

        Args:
            secret_key: Secret key for signing licenses (from environment if not provided).
        """
        self.secret_key = secret_key or os.getenv('LICENSE_SECRET_KEY', self._generate_secret())
        self.license_cache_dir = Path.home() / '.secure-media-processor'
        self.license_file = self.license_cache_dir / 'license.json'
        self.license_cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_secret(self) -> str:
        """Generate a random secret key if none provided."""
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def generate_license_key(
        self,
        email: str,
        license_type: LicenseType,
        duration_days: Optional[int] = 365
    ) -> str:
        """Generate a unique license key.

        Format: XXXX-XXXX-XXXX-XXXX-XXXX (25 characters)

        Args:
            email: Customer email address.
            license_type: Type of license (FREE, PRO, ENTERPRISE).
            duration_days: License duration in days (None = lifetime).

        Returns:
            License key string.
        """
        # Create payload
        timestamp = int(time.time())
        payload = f"{email}:{license_type.value}:{timestamp}"

        # Sign with HMAC
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Take first 20 characters of signature
        key_raw = signature[:20].upper()

        # Format as XXXX-XXXX-XXXX-XXXX-XXXX
        key_parts = [key_raw[i:i+4] for i in range(0, 20, 4)]
        return '-'.join(key_parts)

    def validate_license_key(self, license_key: str) -> bool:
        """Validate license key signature.

        Args:
            license_key: License key to validate.

        Returns:
            True if key signature is valid, False otherwise.
        """
        # Remove dashes
        key_raw = license_key.replace('-', '')

        if len(key_raw) != 20:
            return False

        # For now, basic format validation
        # In production, you'd verify against your database
        return key_raw.isalnum() and key_raw.isupper()

    def create_license(
        self,
        email: str,
        license_type: LicenseType,
        duration_days: Optional[int] = 365,
        max_devices: int = 1
    ) -> License:
        """Create a new license.

        Args:
            email: Customer email.
            license_type: License tier.
            duration_days: License duration (None = lifetime).
            max_devices: Maximum devices that can be activated.

        Returns:
            License object.
        """
        license_key = self.generate_license_key(email, license_type, duration_days)

        issued_at = datetime.now()
        expires_at = None
        if duration_days:
            expires_at = issued_at + timedelta(days=duration_days)

        # Determine features based on license type
        features = self._get_features_for_type(license_type)

        return License(
            license_key=license_key,
            license_type=license_type,
            email=email,
            issued_at=issued_at,
            expires_at=expires_at,
            features=features,
            max_devices=max_devices
        )

    def _get_features_for_type(self, license_type: LicenseType) -> List[str]:
        """Get enabled features for a license type.

        Args:
            license_type: License tier.

        Returns:
            List of enabled feature names.
        """
        if license_type == LicenseType.FREE:
            # Free tier: local encryption only, no cloud, no GPU
            return []

        elif license_type == LicenseType.PRO:
            # Pro tier: cloud storage + GPU + batch processing
            return [
                FeatureFlags.CLOUD_STORAGE.value,
                FeatureFlags.GPU_PROCESSING.value,
                FeatureFlags.BATCH_PROCESSING.value,
            ]

        elif license_type == LicenseType.ENTERPRISE:
            # Enterprise: everything + multi-cloud sync + support
            return [
                FeatureFlags.CLOUD_STORAGE.value,
                FeatureFlags.GPU_PROCESSING.value,
                FeatureFlags.BATCH_PROCESSING.value,
                FeatureFlags.MULTI_CLOUD_SYNC.value,
                FeatureFlags.PRIORITY_SUPPORT.value,
            ]

        return []

    def activate_license(self, license_key: str, email: str) -> License:
        """Activate a license key on this device.

        Args:
            license_key: License key to activate.
            email: Customer email (must match license).

        Returns:
            Activated License object.

        Raises:
            ValueError: If license is invalid or cannot be activated.
        """
        # Validate key format
        if not self.validate_license_key(license_key):
            raise ValueError("Invalid license key format")

        # In production, you'd fetch license from your server/database
        # For now, create a mock license based on key pattern
        # This is where you'd call your licensing server API

        # Mock: Determine license type from key (in production, fetch from server)
        license_type = self._infer_license_type(license_key)

        # Create license object
        license = self.create_license(
            email=email,
            license_type=license_type,
            duration_days=365,
            max_devices=1 if license_type == LicenseType.PRO else 5
        )

        # Get device ID
        device_id = self._get_device_id()

        # Check if device can be activated
        if not license.can_activate_device(device_id):
            raise ValueError(
                f"License already activated on {license.max_devices} device(s). "
                f"Please deactivate a device or upgrade your license."
            )

        # Activate device
        if device_id not in license.activated_devices:
            license.activated_devices.append(device_id)

        # Save license locally
        self._save_license(license)

        return license

    def _infer_license_type(self, license_key: str) -> LicenseType:
        """Infer license type from key pattern (mock implementation).

        In production, fetch from your licensing server.

        Args:
            license_key: License key.

        Returns:
            License type.
        """
        # Mock: Use first character to determine type
        # In production, query your server
        first_char = license_key[0]
        if first_char in ['A', 'B', 'C']:
            return LicenseType.ENTERPRISE
        elif first_char in ['D', 'E', 'F', 'G', 'H']:
            return LicenseType.PRO
        else:
            return LicenseType.FREE

    def _get_device_id(self) -> str:
        """Get unique device identifier.

        Returns:
            Device ID string.
        """
        # Use MAC address + hostname as device ID
        import uuid
        import socket

        mac = uuid.getnode()
        hostname = socket.gethostname()
        device_string = f"{mac}:{hostname}"

        return hashlib.sha256(device_string.encode()).hexdigest()[:16]

    def _save_license(self, license: License) -> None:
        """Save license to local cache.

        Args:
            license: License to save.
        """
        # Set restrictive permissions (owner only)
        self.license_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.license_file, 'w') as f:
            json.dump(license.to_dict(), f, indent=2)

        # Set file permissions to 0600 (owner read/write only)
        os.chmod(self.license_file, 0o600)

    def get_active_license(self) -> Optional[License]:
        """Get currently active license from local cache.

        Returns:
            License object if valid license exists, None otherwise.
        """
        if not self.license_file.exists():
            return None

        try:
            with open(self.license_file, 'r') as f:
                data = json.load(f)

            license = License.from_dict(data)

            # Validate license is still valid
            if not license.is_valid():
                return None

            return license

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def deactivate_license(self) -> bool:
        """Deactivate license on this device.

        Returns:
            True if license was deactivated, False otherwise.
        """
        if self.license_file.exists():
            self.license_file.unlink()
            return True
        return False

    def check_feature(self, feature: FeatureFlags) -> bool:
        """Check if a feature is enabled for the current license.

        Args:
            feature: Feature to check.

        Returns:
            True if feature is enabled, False otherwise.
        """
        license = self.get_active_license()

        if not license:
            # No license = free tier = no premium features
            return False

        return license.is_feature_enabled(feature)

    def get_license_info(self) -> Dict[str, Any]:
        """Get current license information.

        Returns:
            Dictionary with license details.
        """
        license = self.get_active_license()

        if not license:
            return {
                'active': False,
                'type': 'free',
                'features': [],
                'message': 'No active license. Using free tier.'
            }

        days_remaining = None
        if license.expires_at:
            days_remaining = (license.expires_at - datetime.now()).days

        return {
            'active': True,
            'type': license.license_type.value,
            'email': license.email,
            'expires_at': license.expires_at.isoformat() if license.expires_at else 'Never',
            'days_remaining': days_remaining,
            'features': license.features,
            'max_devices': license.max_devices,
            'activated_devices': len(license.activated_devices)
        }


# Global license manager instance
_license_manager = None


def get_license_manager() -> LicenseManager:
    """Get global license manager instance.

    Returns:
        LicenseManager singleton.
    """
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def require_feature(feature: FeatureFlags):
    """Decorator to require a feature for a function.

    Args:
        feature: Feature that must be enabled.

    Raises:
        RuntimeError: If feature is not enabled.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_license_manager()
            if not manager.check_feature(feature):
                raise RuntimeError(
                    f"Feature '{feature.value}' requires a Pro or Enterprise license. "
                    f"Visit https://secure-media-processor.com/pricing to upgrade."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
