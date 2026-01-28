"""Media processing package for Secure Media Processor.

This package provides media processing functionality:
- gpu: GPU-accelerated media processing

Example:
    >>> from src.processing import GPUMediaProcessor
    >>> processor = GPUMediaProcessor()
    >>> result = processor.resize(image, 800, 600)
"""

from .gpu import GPUMediaProcessor, ImageDimensions, FilterConfig

__all__ = [
    'GPUMediaProcessor',
    'ImageDimensions',
    'FilterConfig',
]
