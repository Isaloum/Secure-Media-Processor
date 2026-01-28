"""Medical image preprocessing pipeline for MRI analysis.

This module is maintained for backward compatibility.
New code should import from src.medical.preprocessing instead.
"""

# Re-export from new location for backward compatibility
from src.medical.preprocessing import (
    BreastMRIPreprocessor,
    PreprocessingResult,
    NormalizationMethod,
    SCIPY_AVAILABLE,
    SKIMAGE_AVAILABLE,
    CV2_AVAILABLE,
)

__all__ = [
    'BreastMRIPreprocessor',
    'PreprocessingResult',
    'NormalizationMethod',
    'SCIPY_AVAILABLE',
    'SKIMAGE_AVAILABLE',
    'CV2_AVAILABLE',
]
