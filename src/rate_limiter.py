"""Rate limiting utilities for cloud connector operations.

This module is maintained for backward compatibility.
New code should import from src.core.rate_limiter instead.
"""

# Re-export from new location for backward compatibility
from src.core.rate_limiter import RateLimiter, RateLimitConfig

__all__ = ['RateLimiter', 'RateLimitConfig']
