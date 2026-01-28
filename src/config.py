"""Configuration management for Secure Media Processor.

This module is maintained for backward compatibility.
New code should import from src.core.config instead.
"""

# Re-export from new location for backward compatibility
from src.core.config import Settings, settings

__all__ = ['Settings', 'settings']
