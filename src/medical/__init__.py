"""Medical imaging package for Secure Media Processor.

This package provides medical imaging functionality:
- pipeline: Complete secure medical imaging pipeline
- dicom: DICOM file processing
- preprocessing: MRI preprocessing utilities
- unet: U-Net segmentation models and pipeline
- inference: ML inference pipeline

Example (Simple):
    >>> from src.medical import DICOMProcessor
    >>> processor = DICOMProcessor()
    >>> data, metadata = processor.read_dicom('scan.dcm')

Example (Full Pipeline):
    >>> from src.medical import MedicalPipeline
    >>> pipeline = MedicalPipeline(
    ...     cloud_config={'provider': 's3', 'bucket': 'hospital-data'},
    ...     user_id='researcher@hospital.org'
    ... )
    >>> results = pipeline.process_study(
    ...     remote_path='mri-scans/patient-001/',
    ...     operations=['preprocess', 'segment', 'predict']
    ... )
    >>> print(f"Cancer probability: {results.cancer_probability}")
    >>> pipeline.cleanup()  # Secure deletion
"""

# Main pipeline (integrates everything)
from .pipeline import MedicalPipeline, MedicalStudyResult, ProcessingOperation, create_medical_pipeline

# DICOM processing
from .dicom import DICOMProcessor, DICOMMetadata, DICOMVolumeData

# Preprocessing
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
    # Main Pipeline (NEW - integrates secure transfer + processing)
    'MedicalPipeline',
    'MedicalStudyResult',
    'ProcessingOperation',
    'create_medical_pipeline',
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
