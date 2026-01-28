"""License management package for Secure Media Processor.

This package provides license management functionality:
- manager: License creation, validation, and feature gating

Example:
    >>> from src.licensing import LicenseManager
    >>> manager = LicenseManager('master.key')
    >>> license = manager.generate_license('basic')
"""

from .manager import LicenseManager, License, LicenseType, FeatureFlags

__all__ = [
    'LicenseManager',
    'License',
    'LicenseType',
    'FeatureFlags',
]
