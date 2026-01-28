"""Cloud storage module for secure media backup and synchronization.

This module is maintained for backward compatibility.
New code should import from src.cloud instead.
"""

# Re-export from new location for backward compatibility
from src.cloud.legacy import CloudStorageManager

__all__ = ['CloudStorageManager']
