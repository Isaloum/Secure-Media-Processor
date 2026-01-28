"""Post-processing Utilities for Segmentation Masks.

This module provides post-processing operations for segmentation output:
- Binary thresholding
- Hole filling
- Small object removal
- Morphological operations
- Region property extraction
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

from .config import SegmentationConfig

logger = logging.getLogger(__name__)

# Optional dependencies
SCIPY_AVAILABLE = False
SKIMAGE_AVAILABLE = False

try:
    import scipy.ndimage as ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    logger.debug("scipy not installed - some post-processing features disabled")

try:
    from skimage import morphology, measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    logger.debug("scikit-image not installed - some post-processing features disabled")


class SegmentationPostProcessor:
    """Post-processing utilities for segmentation masks."""

    def __init__(self, config: Optional[SegmentationConfig] = None):
        """Initialize post-processor with configuration.

        Args:
            config: Segmentation configuration
        """
        self.config = config or SegmentationConfig()

    def process(self,
                probability_map: np.ndarray,
                threshold: Optional[float] = None) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Apply full post-processing pipeline.

        Args:
            probability_map: Probability map from model output
            threshold: Optional override for binary threshold

        Returns:
            Tuple of (binary_mask, region_properties)
        """
        thresh = threshold or self.config.threshold

        # Threshold to binary mask
        binary_mask = probability_map > thresh

        if not self.config.apply_post_processing:
            regions = self._extract_region_properties(binary_mask)
            return binary_mask.astype(np.uint8), regions

        # Fill holes
        if self.config.fill_holes:
            binary_mask = self.fill_holes(binary_mask)

        # Remove small objects
        if self.config.min_object_size > 0:
            binary_mask = self.remove_small_objects(binary_mask, self.config.min_object_size)

        # Extract region properties
        regions = self._extract_region_properties(binary_mask)

        return binary_mask.astype(np.uint8), regions

    def fill_holes(self, mask: np.ndarray) -> np.ndarray:
        """Fill holes in binary mask.

        Args:
            mask: Binary mask with potential holes

        Returns:
            Mask with holes filled
        """
        if SCIPY_AVAILABLE:
            return ndimage.binary_fill_holes(mask)
        elif SKIMAGE_AVAILABLE:
            return morphology.remove_small_holes(mask)
        return mask

    def remove_small_objects(self, mask: np.ndarray, min_size: int) -> np.ndarray:
        """Remove small connected components.

        Args:
            mask: Binary mask
            min_size: Minimum object size in pixels

        Returns:
            Mask with small objects removed
        """
        if SKIMAGE_AVAILABLE:
            return morphology.remove_small_objects(mask, min_size=min_size)
        elif SCIPY_AVAILABLE:
            labeled, num_features = ndimage.label(mask)
            if num_features == 0:
                return mask

            sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
            for i, size in enumerate(sizes, 1):
                if size < min_size:
                    mask[labeled == i] = 0
        return mask

    def apply_morphology(self,
                         mask: np.ndarray,
                         operation: str = 'close',
                         kernel_size: int = 3) -> np.ndarray:
        """Apply morphological operation.

        Args:
            mask: Binary mask
            operation: 'dilate', 'erode', 'open', 'close'
            kernel_size: Size of structuring element

        Returns:
            Processed mask
        """
        if SCIPY_AVAILABLE:
            structure = np.ones((kernel_size, kernel_size))

            if operation == 'dilate':
                return ndimage.binary_dilation(mask, structure=structure)
            elif operation == 'erode':
                return ndimage.binary_erosion(mask, structure=structure)
            elif operation == 'open':
                eroded = ndimage.binary_erosion(mask, structure=structure)
                return ndimage.binary_dilation(eroded, structure=structure)
            elif operation == 'close':
                dilated = ndimage.binary_dilation(mask, structure=structure)
                return ndimage.binary_erosion(dilated, structure=structure)

        return mask

    def smooth_boundaries(self, mask: np.ndarray, iterations: int = 1) -> np.ndarray:
        """Smooth mask boundaries using morphological operations.

        Args:
            mask: Binary mask
            iterations: Number of smoothing iterations

        Returns:
            Mask with smoother boundaries
        """
        result = mask.copy()
        for _ in range(iterations):
            result = self.apply_morphology(result, 'close', 3)
            result = self.apply_morphology(result, 'open', 3)
        return result

    def _extract_region_properties(self, mask: np.ndarray) -> List[Dict[str, Any]]:
        """Extract properties for each connected region.

        Args:
            mask: Binary mask

        Returns:
            List of region property dictionaries
        """
        regions = []

        if SKIMAGE_AVAILABLE:
            labeled = measure.label(mask)
            props = measure.regionprops(labeled)

            for prop in props:
                regions.append({
                    'label': prop.label,
                    'area': prop.area,
                    'centroid': prop.centroid,
                    'bbox': prop.bbox,
                    'perimeter': prop.perimeter,
                    'eccentricity': prop.eccentricity,
                    'solidity': prop.solidity
                })
        elif SCIPY_AVAILABLE:
            labeled, num_features = ndimage.label(mask)
            for i in range(1, num_features + 1):
                region_mask = labeled == i
                coords = np.argwhere(region_mask)
                if len(coords) > 0:
                    regions.append({
                        'label': i,
                        'area': int(np.sum(region_mask)),
                        'centroid': tuple(coords.mean(axis=0)),
                        'bbox': (coords[:, 0].min(), coords[:, 1].min(),
                                coords[:, 0].max(), coords[:, 1].max())
                    })

        return regions

    def get_largest_component(self, mask: np.ndarray) -> np.ndarray:
        """Keep only the largest connected component.

        Args:
            mask: Binary mask with multiple components

        Returns:
            Mask with only the largest component
        """
        if SKIMAGE_AVAILABLE:
            labeled = measure.label(mask)
            if labeled.max() == 0:
                return mask

            props = measure.regionprops(labeled)
            largest = max(props, key=lambda x: x.area)
            return (labeled == largest.label).astype(mask.dtype)

        elif SCIPY_AVAILABLE:
            labeled, num_features = ndimage.label(mask)
            if num_features == 0:
                return mask

            sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
            largest_label = np.argmax(sizes) + 1
            return (labeled == largest_label).astype(mask.dtype)

        return mask
