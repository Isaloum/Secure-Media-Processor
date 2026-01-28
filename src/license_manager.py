"""License management system for Secure Media Processor.

This module is maintained for backward compatibility.
New code should import from src.licensing instead.
"""

# Re-export from new location for backward compatibility
from src.licensing.manager import LicenseManager, License, LicenseType, FeatureFlags

__all__ = ['LicenseManager', 'License', 'LicenseType', 'FeatureFlags']
