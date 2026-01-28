"""Encryption module for secure media handling.

This module is maintained for backward compatibility.
New code should import from src.core.encryption instead.
"""

# Re-export from new location for backward compatibility
from src.core.encryption import MediaEncryptor

__all__ = ['MediaEncryptor']
