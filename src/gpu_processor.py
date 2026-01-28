"""GPU-accelerated media processing module.

This module is maintained for backward compatibility.
New code should import from src.processing instead.
"""

# Re-export from new location for backward compatibility
from src.processing.gpu import GPUMediaProcessor, ImageDimensions, FilterConfig

__all__ = ['GPUMediaProcessor', 'ImageDimensions', 'FilterConfig']
