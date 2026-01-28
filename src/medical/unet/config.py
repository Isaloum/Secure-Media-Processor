"""Configuration and Data Classes for U-Net Segmentation.

This module provides configuration and result data classes:
- SegmentationConfig: Model and inference settings
- SegmentationResult: Inference output container
"""

from __future__ import annotations

from typing import Tuple, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class UNetVariant(Enum):
    """U-Net architecture variants."""
    STANDARD = "standard"
    ATTENTION = "attention"
    RESIDUAL = "residual"


@dataclass
class SegmentationConfig:
    """Configuration for U-Net segmentation."""
    # Model architecture
    variant: UNetVariant = UNetVariant.STANDARD
    in_channels: int = 1
    out_channels: int = 1  # Binary segmentation
    base_features: int = 64  # Features in first layer
    depth: int = 4  # Encoder/decoder depth

    # Input configuration
    input_size: Tuple[int, int] = (256, 256)
    normalize_input: bool = True

    # Inference configuration
    use_gpu: bool = True
    batch_size: int = 1
    threshold: float = 0.5  # Binary mask threshold

    # Post-processing
    apply_post_processing: bool = True
    min_object_size: int = 100  # Minimum pixels for valid region
    fill_holes: bool = True

    # Multi-class segmentation
    num_classes: int = 1
    class_names: List[str] = field(default_factory=lambda: ["Tumor"])


@dataclass
class SegmentationResult:
    """Result of segmentation inference."""
    # Binary segmentation mask
    mask: np.ndarray

    # Probability map (before thresholding)
    probability_map: np.ndarray

    # Original image shape
    original_shape: Tuple[int, ...]

    # Segmentation statistics
    num_regions: int
    total_area: int  # Total segmented pixels

    # Region properties
    regions: List[Dict[str, Any]] = field(default_factory=list)

    # Processing metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'num_regions': self.num_regions,
            'total_area': self.total_area,
            'regions': self.regions,
            'metadata': self.metadata,
            'mask_shape': list(self.mask.shape)
        }

    @property
    def has_detections(self) -> bool:
        """Check if any regions were detected."""
        return self.num_regions > 0

    @property
    def coverage_ratio(self) -> float:
        """Calculate ratio of segmented area to total image area."""
        total_pixels = np.prod(self.original_shape)
        return self.total_area / total_pixels if total_pixels > 0 else 0.0
