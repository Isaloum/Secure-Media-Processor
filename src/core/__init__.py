"""Core functionality for Secure Media Processor.

This package provides core infrastructure components:
- encryption: AES-256-GCM file encryption
- config: Application settings management
- rate_limiter: API rate limiting utilities
"""

from .encryption import MediaEncryptor
from .config import Settings, settings
from .rate_limiter import RateLimiter, RateLimitConfig

__all__ = [
    'MediaEncryptor',
    'Settings',
    'settings',
    'RateLimiter',
    'RateLimitConfig',
]
