"""Evaluation Metrics for Segmentation Tasks.

This module provides metrics for evaluating segmentation quality:
- Dice coefficient (overlap)
- IoU/Jaccard index
- Precision, Recall, Specificity
- Hausdorff distance (boundary accuracy)
- Average surface distance
"""

from __future__ import annotations

import logging
from typing import Dict
import numpy as np

logger = logging.getLogger(__name__)

# Optional dependencies
SCIPY_AVAILABLE = False

try:
    import scipy.ndimage as ndimage
    from scipy.spatial.distance import directed_hausdorff
    from scipy.spatial import cKDTree
    SCIPY_AVAILABLE = True
except ImportError:
    logger.debug("scipy not installed - some metrics unavailable")


class SegmentationMetrics:
    """Evaluation metrics for segmentation tasks."""

    @staticmethod
    def dice_coefficient(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate Dice similarity coefficient.

        Dice = 2 * |A intersection B| / (|A| + |B|)

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor to avoid division by zero

        Returns:
            Dice coefficient (0-1, higher is better)
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        intersection = np.sum(pred & target)
        return (2.0 * intersection + smooth) / (np.sum(pred) + np.sum(target) + smooth)

    @staticmethod
    def iou(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate Intersection over Union (Jaccard index).

        IoU = |A intersection B| / |A union B|

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor

        Returns:
            IoU score (0-1, higher is better)
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        intersection = np.sum(pred & target)
        union = np.sum(pred | target)

        return (intersection + smooth) / (union + smooth)

    @staticmethod
    def precision(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate precision.

        Precision = TP / (TP + FP)

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor

        Returns:
            Precision score (0-1)
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        tp = np.sum(pred & target)
        fp = np.sum(pred & ~target)

        return (tp + smooth) / (tp + fp + smooth)

    @staticmethod
    def recall(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate recall (sensitivity).

        Recall = TP / (TP + FN)

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor

        Returns:
            Recall score (0-1)
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        tp = np.sum(pred & target)
        fn = np.sum(~pred & target)

        return (tp + smooth) / (tp + fn + smooth)

    @staticmethod
    def specificity(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate specificity.

        Specificity = TN / (TN + FP)

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor

        Returns:
            Specificity score (0-1)
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        tn = np.sum(~pred & ~target)
        fp = np.sum(pred & ~target)

        return (tn + smooth) / (tn + fp + smooth)

    @staticmethod
    def f1_score(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
        """Calculate F1 score (harmonic mean of precision and recall).

        F1 = 2 * (precision * recall) / (precision + recall)

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            smooth: Smoothing factor

        Returns:
            F1 score (0-1)
        """
        prec = SegmentationMetrics.precision(pred, target, smooth)
        rec = SegmentationMetrics.recall(pred, target, smooth)
        return (2 * prec * rec + smooth) / (prec + rec + smooth)

    @staticmethod
    def hausdorff_distance(pred: np.ndarray, target: np.ndarray) -> float:
        """Calculate Hausdorff distance between prediction and target boundaries.

        Lower is better. Returns infinity if either mask is empty.

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask

        Returns:
            Hausdorff distance in pixels
        """
        if not SCIPY_AVAILABLE:
            logger.warning("scipy required for Hausdorff distance")
            return float('inf')

        # Get boundary points
        pred_points = np.argwhere(pred > 0)
        target_points = np.argwhere(target > 0)

        if len(pred_points) == 0 or len(target_points) == 0:
            return float('inf')

        # Calculate bidirectional Hausdorff distance
        forward = directed_hausdorff(pred_points, target_points)[0]
        backward = directed_hausdorff(target_points, pred_points)[0]

        return max(forward, backward)

    @staticmethod
    def average_surface_distance(pred: np.ndarray, target: np.ndarray) -> float:
        """Calculate average surface distance (ASD).

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask

        Returns:
            Average surface distance in pixels
        """
        if not SCIPY_AVAILABLE:
            logger.warning("scipy required for surface distance")
            return float('inf')

        pred_points = np.argwhere(pred > 0)
        target_points = np.argwhere(target > 0)

        if len(pred_points) == 0 or len(target_points) == 0:
            return float('inf')

        # Calculate distances from each pred point to nearest target point
        target_tree = cKDTree(target_points)
        pred_to_target, _ = target_tree.query(pred_points)

        pred_tree = cKDTree(pred_points)
        target_to_pred, _ = pred_tree.query(target_points)

        # Average of both directions
        return (pred_to_target.mean() + target_to_pred.mean()) / 2

    @classmethod
    def evaluate(cls,
                 pred: np.ndarray,
                 target: np.ndarray,
                 include_surface_metrics: bool = True) -> Dict[str, float]:
        """Calculate all segmentation metrics.

        Args:
            pred: Predicted binary mask
            target: Ground truth binary mask
            include_surface_metrics: Include Hausdorff and ASD (slower)

        Returns:
            Dictionary of all metrics
        """
        metrics = {
            'dice': cls.dice_coefficient(pred, target),
            'iou': cls.iou(pred, target),
            'precision': cls.precision(pred, target),
            'recall': cls.recall(pred, target),
            'specificity': cls.specificity(pred, target),
            'f1': cls.f1_score(pred, target)
        }

        if include_surface_metrics:
            metrics['hausdorff_distance'] = cls.hausdorff_distance(pred, target)
            metrics['average_surface_distance'] = cls.average_surface_distance(pred, target)

        return metrics
