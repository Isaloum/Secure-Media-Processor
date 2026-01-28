"""Medical imaging package for Secure Media Processor.

This package provides medical imaging functionality:
- dicom: DICOM file processing
- preprocessing: MRI preprocessing utilities
- unet: U-Net segmentation models and pipeline
- inference: ML inference pipeline

Example:
    >>> from src.medical import DICOMProcessor
    >>> processor = DICOMProcessor()
    >>> data, metadata = processor.read_dicom('scan.dcm')
"""

from .dicom import DICOMProcessor, DICOMMetadata, DICOMVolumeData
from .preprocessing import BreastMRIPreprocessor, PreprocessingResult

# U-Net segmentation
from .unet import (
    UNetVariant,
    SegmentationConfig,
    SegmentationResult,
    UNetSegmentation,
    SegmentationMetrics,
    SegmentationPostProcessor,
    check_segmentation_available,
)

__all__ = [
    # DICOM
    'DICOMProcessor',
    'DICOMMetadata',
    'DICOMVolumeData',
    # Preprocessing
    'BreastMRIPreprocessor',
    'PreprocessingResult',
    # U-Net
    'UNetVariant',
    'SegmentationConfig',
    'SegmentationResult',
    'UNetSegmentation',
    'SegmentationMetrics',
    'SegmentationPostProcessor',
    'check_segmentation_available',
]
