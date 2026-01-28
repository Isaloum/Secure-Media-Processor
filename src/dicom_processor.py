"""DICOM medical image processing module.

This module is maintained for backward compatibility.
New code should import from src.medical.dicom instead.
"""

# Re-export from new location for backward compatibility
from src.medical.dicom import (
    DICOMProcessor,
    DICOMMetadata,
    DICOMVolumeData,
    PYDICOM_AVAILABLE,
)

__all__ = [
    'DICOMProcessor',
    'DICOMMetadata',
    'DICOMVolumeData',
    'PYDICOM_AVAILABLE',
]
