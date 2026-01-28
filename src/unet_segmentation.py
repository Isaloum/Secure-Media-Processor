"""U-Net Segmentation for Medical Image Analysis.

This module provides U-Net architecture and inference pipeline
for tumor/lesion segmentation in medical images, particularly
breast MRI analysis.

Features:
- Standard U-Net encoder-decoder architecture
- Attention U-Net variant for improved performance
- Post-processing utilities (morphological ops, connected components)
- Evaluation metrics (Dice, IoU, Hausdorff distance)
- GPU-accelerated inference
- 2D and 3D segmentation support
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# Optional dependencies
TORCH_AVAILABLE = False
SCIPY_AVAILABLE = False
SKIMAGE_AVAILABLE = False
torch = None
nn = None
F = None

try:
    import torch as _torch
    import torch.nn as _nn
    import torch.nn.functional as _F
    torch = _torch
    nn = _nn
    F = _F
    TORCH_AVAILABLE = True
    logger.debug("PyTorch available for U-Net segmentation")
except ImportError:
    logger.info("PyTorch not installed - U-Net segmentation unavailable")

try:
    import scipy.ndimage as ndimage
    from scipy.spatial.distance import directed_hausdorff
    SCIPY_AVAILABLE = True
except ImportError:
    logger.debug("scipy not installed - some post-processing features disabled")

try:
    from skimage import morphology, measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    logger.debug("scikit-image not installed - some post-processing features disabled")


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


# ============================================================================
# U-Net Architecture
# ============================================================================

if TORCH_AVAILABLE:

    class DoubleConv(nn.Module):
        """Double convolution block: (Conv -> BN -> ReLU) x 2."""

        def __init__(self, in_channels: int, out_channels: int, mid_channels: Optional[int] = None):
            super().__init__()
            mid_channels = mid_channels or out_channels
            self.double_conv = nn.Sequential(
                nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(mid_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            )

        def forward(self, x):
            return self.double_conv(x)


    class Down(nn.Module):
        """Downsampling block: MaxPool -> DoubleConv."""

        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.maxpool_conv = nn.Sequential(
                nn.MaxPool2d(2),
                DoubleConv(in_channels, out_channels)
            )

        def forward(self, x):
            return self.maxpool_conv(x)


    class Up(nn.Module):
        """Upsampling block: Upsample -> Concatenate -> DoubleConv."""

        def __init__(self, in_channels: int, out_channels: int, bilinear: bool = True):
            super().__init__()
            if bilinear:
                self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
                self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
            else:
                self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
                self.conv = DoubleConv(in_channels, out_channels)

        def forward(self, x1, x2):
            x1 = self.up(x1)

            # Handle size mismatch
            diff_y = x2.size()[2] - x1.size()[2]
            diff_x = x2.size()[3] - x1.size()[3]
            x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2,
                           diff_y // 2, diff_y - diff_y // 2])

            # Concatenate skip connection
            x = torch.cat([x2, x1], dim=1)
            return self.conv(x)


    class AttentionGate(nn.Module):
        """Attention gate for Attention U-Net."""

        def __init__(self, gate_channels: int, feature_channels: int, inter_channels: int):
            super().__init__()
            self.W_g = nn.Sequential(
                nn.Conv2d(gate_channels, inter_channels, kernel_size=1, bias=True),
                nn.BatchNorm2d(inter_channels)
            )
            self.W_x = nn.Sequential(
                nn.Conv2d(feature_channels, inter_channels, kernel_size=1, bias=True),
                nn.BatchNorm2d(inter_channels)
            )
            self.psi = nn.Sequential(
                nn.Conv2d(inter_channels, 1, kernel_size=1, bias=True),
                nn.BatchNorm2d(1),
                nn.Sigmoid()
            )
            self.relu = nn.ReLU(inplace=True)

        def forward(self, g, x):
            g1 = self.W_g(g)
            x1 = self.W_x(x)

            # Handle size mismatch
            if g1.shape[2:] != x1.shape[2:]:
                g1 = F.interpolate(g1, size=x1.shape[2:], mode='bilinear', align_corners=True)

            psi = self.relu(g1 + x1)
            psi = self.psi(psi)
            return x * psi


    class UNet(nn.Module):
        """Standard U-Net architecture for medical image segmentation.

        Architecture:
        - Encoder: 4 downsampling blocks with skip connections
        - Bottleneck: Deepest feature representation
        - Decoder: 4 upsampling blocks with skip connection concatenation
        - Output: 1x1 convolution to desired number of output channels

        Args:
            in_channels: Number of input channels (1 for grayscale)
            out_channels: Number of output channels (classes)
            base_features: Number of features in first layer (doubles each layer)
            bilinear: Use bilinear upsampling (vs transposed conv)
        """

        def __init__(self,
                     in_channels: int = 1,
                     out_channels: int = 1,
                     base_features: int = 64,
                     bilinear: bool = True):
            super().__init__()
            self.in_channels = in_channels
            self.out_channels = out_channels
            self.bilinear = bilinear

            # Feature sizes: 64 -> 128 -> 256 -> 512 -> 1024
            f = base_features
            factor = 2 if bilinear else 1

            # Encoder
            self.inc = DoubleConv(in_channels, f)
            self.down1 = Down(f, f * 2)
            self.down2 = Down(f * 2, f * 4)
            self.down3 = Down(f * 4, f * 8)
            self.down4 = Down(f * 8, f * 16 // factor)

            # Decoder
            self.up1 = Up(f * 16, f * 8 // factor, bilinear)
            self.up2 = Up(f * 8, f * 4 // factor, bilinear)
            self.up3 = Up(f * 4, f * 2 // factor, bilinear)
            self.up4 = Up(f * 2, f, bilinear)

            # Output layer
            self.outc = nn.Conv2d(f, out_channels, kernel_size=1)

        def forward(self, x):
            # Encoder path with skip connections
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.down4(x4)

            # Decoder path with skip connections
            x = self.up1(x5, x4)
            x = self.up2(x, x3)
            x = self.up3(x, x2)
            x = self.up4(x, x1)

            # Output
            logits = self.outc(x)
            return logits


    class AttentionUNet(nn.Module):
        """Attention U-Net with attention gates for improved feature selection.

        Reference: Oktay et al., "Attention U-Net: Learning Where to Look
        for the Pancreas" (2018)
        """

        def __init__(self,
                     in_channels: int = 1,
                     out_channels: int = 1,
                     base_features: int = 64):
            super().__init__()
            self.in_channels = in_channels
            self.out_channels = out_channels

            f = base_features

            # Encoder
            self.inc = DoubleConv(in_channels, f)
            self.down1 = Down(f, f * 2)
            self.down2 = Down(f * 2, f * 4)
            self.down3 = Down(f * 4, f * 8)
            self.down4 = Down(f * 8, f * 16)

            # Attention gates
            self.att4 = AttentionGate(f * 16, f * 8, f * 4)
            self.att3 = AttentionGate(f * 8, f * 4, f * 2)
            self.att2 = AttentionGate(f * 4, f * 2, f)
            self.att1 = AttentionGate(f * 2, f, f // 2)

            # Decoder with transposed convolutions
            self.up4 = nn.ConvTranspose2d(f * 16, f * 8, kernel_size=2, stride=2)
            self.conv4 = DoubleConv(f * 16, f * 8)

            self.up3 = nn.ConvTranspose2d(f * 8, f * 4, kernel_size=2, stride=2)
            self.conv3 = DoubleConv(f * 8, f * 4)

            self.up2 = nn.ConvTranspose2d(f * 4, f * 2, kernel_size=2, stride=2)
            self.conv2 = DoubleConv(f * 4, f * 2)

            self.up1 = nn.ConvTranspose2d(f * 2, f, kernel_size=2, stride=2)
            self.conv1 = DoubleConv(f * 2, f)

            # Output
            self.outc = nn.Conv2d(f, out_channels, kernel_size=1)

        def forward(self, x):
            # Encoder
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.down4(x4)

            # Decoder with attention
            d4 = self.up4(x5)
            x4 = self.att4(d4, x4)
            d4 = self._pad_and_concat(d4, x4)
            d4 = self.conv4(d4)

            d3 = self.up3(d4)
            x3 = self.att3(d3, x3)
            d3 = self._pad_and_concat(d3, x3)
            d3 = self.conv3(d3)

            d2 = self.up2(d3)
            x2 = self.att2(d2, x2)
            d2 = self._pad_and_concat(d2, x2)
            d2 = self.conv2(d2)

            d1 = self.up1(d2)
            x1 = self.att1(d1, x1)
            d1 = self._pad_and_concat(d1, x1)
            d1 = self.conv1(d1)

            return self.outc(d1)

        def _pad_and_concat(self, x1, x2):
            """Pad x1 to match x2 and concatenate."""
            diff_y = x2.size()[2] - x1.size()[2]
            diff_x = x2.size()[3] - x1.size()[3]
            x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2,
                           diff_y // 2, diff_y - diff_y // 2])
            return torch.cat([x2, x1], dim=1)


    class ResidualDoubleConv(nn.Module):
        """Double convolution with residual connection."""

        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.double_conv = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels)
            )

            # Skip connection
            self.skip = nn.Sequential()
            if in_channels != out_channels:
                self.skip = nn.Sequential(
                    nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                    nn.BatchNorm2d(out_channels)
                )

            self.relu = nn.ReLU(inplace=True)

        def forward(self, x):
            return self.relu(self.double_conv(x) + self.skip(x))


    class ResidualUNet(nn.Module):
        """U-Net with residual connections for deeper training."""

        def __init__(self,
                     in_channels: int = 1,
                     out_channels: int = 1,
                     base_features: int = 64):
            super().__init__()
            f = base_features

            # Encoder
            self.inc = ResidualDoubleConv(in_channels, f)
            self.down1 = nn.Sequential(nn.MaxPool2d(2), ResidualDoubleConv(f, f * 2))
            self.down2 = nn.Sequential(nn.MaxPool2d(2), ResidualDoubleConv(f * 2, f * 4))
            self.down3 = nn.Sequential(nn.MaxPool2d(2), ResidualDoubleConv(f * 4, f * 8))
            self.down4 = nn.Sequential(nn.MaxPool2d(2), ResidualDoubleConv(f * 8, f * 16))

            # Decoder
            self.up4 = nn.ConvTranspose2d(f * 16, f * 8, kernel_size=2, stride=2)
            self.conv4 = ResidualDoubleConv(f * 16, f * 8)

            self.up3 = nn.ConvTranspose2d(f * 8, f * 4, kernel_size=2, stride=2)
            self.conv3 = ResidualDoubleConv(f * 8, f * 4)

            self.up2 = nn.ConvTranspose2d(f * 4, f * 2, kernel_size=2, stride=2)
            self.conv2 = ResidualDoubleConv(f * 4, f * 2)

            self.up1 = nn.ConvTranspose2d(f * 2, f, kernel_size=2, stride=2)
            self.conv1 = ResidualDoubleConv(f * 2, f)

            self.outc = nn.Conv2d(f, out_channels, kernel_size=1)

        def forward(self, x):
            # Encoder
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.down4(x4)

            # Decoder
            d4 = self.up4(x5)
            d4 = self._pad_and_concat(d4, x4)
            d4 = self.conv4(d4)

            d3 = self.up3(d4)
            d3 = self._pad_and_concat(d3, x3)
            d3 = self.conv3(d3)

            d2 = self.up2(d3)
            d2 = self._pad_and_concat(d2, x2)
            d2 = self.conv2(d2)

            d1 = self.up1(d2)
            d1 = self._pad_and_concat(d1, x1)
            d1 = self.conv1(d1)

            return self.outc(d1)

        def _pad_and_concat(self, x1, x2):
            diff_y = x2.size()[2] - x1.size()[2]
            diff_x = x2.size()[3] - x1.size()[3]
            x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2,
                           diff_y // 2, diff_y - diff_y // 2])
            return torch.cat([x2, x1], dim=1)


# ============================================================================
# Loss Functions for Segmentation Training
# ============================================================================

if TORCH_AVAILABLE:

    class DiceLoss(nn.Module):
        """Dice loss for segmentation training."""

        def __init__(self, smooth: float = 1.0):
            super().__init__()
            self.smooth = smooth

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            predictions = torch.sigmoid(predictions)
            predictions = predictions.view(-1)
            targets = targets.view(-1)

            intersection = (predictions * targets).sum()
            dice = (2. * intersection + self.smooth) / (predictions.sum() + targets.sum() + self.smooth)

            return 1 - dice


    class BCEDiceLoss(nn.Module):
        """Combined BCE and Dice loss."""

        def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5):
            super().__init__()
            self.bce_weight = bce_weight
            self.dice_weight = dice_weight
            self.bce = nn.BCEWithLogitsLoss()
            self.dice = DiceLoss()

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            bce_loss = self.bce(predictions, targets)
            dice_loss = self.dice(predictions, targets)
            return self.bce_weight * bce_loss + self.dice_weight * dice_loss


    class FocalLoss(nn.Module):
        """Focal loss for handling class imbalance."""

        def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
            super().__init__()
            self.alpha = alpha
            self.gamma = gamma

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            bce = F.binary_cross_entropy_with_logits(predictions, targets, reduction='none')
            pt = torch.exp(-bce)
            focal_loss = self.alpha * (1 - pt) ** self.gamma * bce
            return focal_loss.mean()


# ============================================================================
# Evaluation Metrics
# ============================================================================

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
        """
        pred = pred.astype(bool).flatten()
        target = target.astype(bool).flatten()

        tn = np.sum(~pred & ~target)
        fp = np.sum(pred & ~target)

        return (tn + smooth) / (tn + fp + smooth)

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
        from scipy.spatial import cKDTree
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
            'specificity': cls.specificity(pred, target)
        }

        if include_surface_metrics:
            metrics['hausdorff_distance'] = cls.hausdorff_distance(pred, target)
            metrics['average_surface_distance'] = cls.average_surface_distance(pred, target)

        return metrics


# ============================================================================
# Post-processing Utilities
# ============================================================================

class SegmentationPostProcessor:
    """Post-processing utilities for segmentation masks."""

    def __init__(self, config: Optional[SegmentationConfig] = None):
        """Initialize post-processor with configuration."""
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
        """Fill holes in binary mask."""
        if SCIPY_AVAILABLE:
            return ndimage.binary_fill_holes(mask)
        elif SKIMAGE_AVAILABLE:
            return morphology.remove_small_holes(mask)
        return mask

    def remove_small_objects(self, mask: np.ndarray, min_size: int) -> np.ndarray:
        """Remove small connected components."""
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

    def _extract_region_properties(self, mask: np.ndarray) -> List[Dict[str, Any]]:
        """Extract properties for each connected region."""
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


# ============================================================================
# Segmentation Inference Pipeline
# ============================================================================

class UNetSegmentation:
    """U-Net segmentation inference pipeline.

    Provides end-to-end segmentation from image to processed mask
    with support for preprocessing, inference, and post-processing.
    """

    def __init__(self, config: Optional[SegmentationConfig] = None):
        """Initialize segmentation pipeline.

        Args:
            config: Segmentation configuration
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required for U-Net segmentation. Install with: pip install torch")

        self.config = config or SegmentationConfig()
        self.model = None
        self.device = None
        self.post_processor = SegmentationPostProcessor(self.config)

        self._setup_device()

    def _setup_device(self):
        """Setup compute device."""
        if self.config.use_gpu and torch.cuda.is_available():
            self.device = torch.device('cuda')
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        elif self.config.use_gpu and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = torch.device('mps')
            logger.info("Using Apple Metal GPU")
        else:
            self.device = torch.device('cpu')
            logger.info("Using CPU for inference")

    def create_model(self, variant: Optional[UNetVariant] = None) -> None:
        """Create U-Net model architecture.

        Args:
            variant: U-Net variant to use (overrides config)
        """
        var = variant or self.config.variant

        if var == UNetVariant.STANDARD:
            self.model = UNet(
                in_channels=self.config.in_channels,
                out_channels=self.config.out_channels,
                base_features=self.config.base_features
            )
        elif var == UNetVariant.ATTENTION:
            self.model = AttentionUNet(
                in_channels=self.config.in_channels,
                out_channels=self.config.out_channels,
                base_features=self.config.base_features
            )
        elif var == UNetVariant.RESIDUAL:
            self.model = ResidualUNet(
                in_channels=self.config.in_channels,
                out_channels=self.config.out_channels,
                base_features=self.config.base_features
            )

        self.model = self.model.to(self.device)
        self.model.eval()
        logger.info(f"Created {var.value} U-Net model")

    def load_model(self, model_path: Union[str, Path]) -> None:
        """Load trained model weights.

        Args:
            model_path: Path to model weights (.pt or .pth file)
        """
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        # Create model architecture if not already created
        if self.model is None:
            self.create_model()

        # Load weights
        state_dict = torch.load(str(path), map_location=self.device)

        # Handle different save formats
        if 'model_state_dict' in state_dict:
            state_dict = state_dict['model_state_dict']
        elif 'state_dict' in state_dict:
            state_dict = state_dict['state_dict']

        self.model.load_state_dict(state_dict)
        self.model.eval()
        logger.info(f"Loaded model weights from {path}")

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for model input.

        Args:
            image: Input image (2D numpy array)

        Returns:
            Preprocessed tensor
        """
        # Ensure float32
        image = image.astype(np.float32)

        # Normalize if configured
        if self.config.normalize_input:
            # Z-score normalization
            mask = image > 0
            if mask.any():
                mean = image[mask].mean()
                std = image[mask].std()
                if std > 0:
                    image = (image - mean) / std

        # Resize if needed
        target_h, target_w = self.config.input_size
        if image.shape != (target_h, target_w):
            if SCIPY_AVAILABLE:
                zoom_factors = (target_h / image.shape[0], target_w / image.shape[1])
                image = ndimage.zoom(image, zoom_factors, order=1)
            else:
                logger.warning("scipy not available for resizing, using original size")

        # Add batch and channel dimensions: (H, W) -> (1, 1, H, W)
        tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0)

        return tensor.to(self.device)

    def segment(self, image: np.ndarray) -> SegmentationResult:
        """Segment a single image.

        Args:
            image: Input image (2D numpy array)

        Returns:
            SegmentationResult with mask and metadata
        """
        if self.model is None:
            self.create_model()

        original_shape = image.shape

        # Preprocess
        input_tensor = self._preprocess(image)

        # Inference
        with torch.no_grad():
            output = self.model(input_tensor)
            probability_map = torch.sigmoid(output).cpu().numpy()[0, 0]

        # Resize probability map back to original size if needed
        if probability_map.shape != original_shape and SCIPY_AVAILABLE:
            zoom_factors = (original_shape[0] / probability_map.shape[0],
                           original_shape[1] / probability_map.shape[1])
            probability_map = ndimage.zoom(probability_map, zoom_factors, order=1)

        # Post-process
        binary_mask, regions = self.post_processor.process(probability_map)

        return SegmentationResult(
            mask=binary_mask,
            probability_map=probability_map,
            original_shape=original_shape,
            num_regions=len(regions),
            total_area=int(np.sum(binary_mask)),
            regions=regions,
            metadata={
                'threshold': self.config.threshold,
                'variant': self.config.variant.value,
                'device': str(self.device)
            }
        )

    def segment_volume(self,
                       volume: np.ndarray,
                       aggregate_3d: bool = False) -> List[SegmentationResult]:
        """Segment 3D volume slice by slice.

        Args:
            volume: 3D volume (slices, height, width)
            aggregate_3d: If True, apply 3D post-processing

        Returns:
            List of SegmentationResults, one per slice
        """
        results = []

        for i in range(volume.shape[0]):
            slice_2d = volume[i]
            result = self.segment(slice_2d)
            results.append(result)

        if aggregate_3d and SCIPY_AVAILABLE:
            # Stack masks and apply 3D connected components
            volume_mask = np.stack([r.mask for r in results], axis=0)

            # 3D hole filling
            volume_mask = ndimage.binary_fill_holes(volume_mask)

            # Update results with 3D processed masks
            for i, result in enumerate(results):
                result.mask = volume_mask[i]
                result.total_area = int(np.sum(volume_mask[i]))

        return results

    def segment_from_dicom(self,
                           dicom_path: Union[str, Path],
                           preprocess: bool = True) -> Dict[str, Any]:
        """Segment from DICOM file or directory.

        Args:
            dicom_path: Path to DICOM file or series directory
            preprocess: Apply medical preprocessing before segmentation

        Returns:
            Dictionary with segmentation results and metadata
        """
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()
        dicom_path = Path(dicom_path)

        if dicom_path.is_dir():
            volume_data = processor.read_dicom_series(dicom_path)
            pixel_data = volume_data.pixel_data
            metadata = volume_data.slice_metadata[0]
        else:
            pixel_data, metadata = processor.read_dicom(dicom_path)

        # Preprocess if requested
        if preprocess:
            from src.medical_preprocessing import BreastMRIPreprocessor
            preprocessor = BreastMRIPreprocessor()
            if pixel_data.ndim == 3:
                pixel_data = preprocessor.preprocess_for_prediction(pixel_data)
            else:
                result = preprocessor.preprocess(pixel_data)
                pixel_data = result.data

        # Segment
        if pixel_data.ndim == 3:
            results = self.segment_volume(pixel_data, aggregate_3d=True)

            # Calculate volume statistics
            total_volume = sum(r.total_area for r in results)
            max_area_slice = max(range(len(results)), key=lambda i: results[i].total_area)

            return {
                'results': results,
                'num_slices': len(results),
                'total_volume_pixels': total_volume,
                'max_area_slice': max_area_slice,
                'dicom_metadata': {
                    'modality': metadata.modality,
                    'series_description': metadata.series_description,
                    'study_date': metadata.study_date
                }
            }
        else:
            result = self.segment(pixel_data)
            return {
                'result': result,
                'dicom_metadata': {
                    'modality': metadata.modality,
                    'series_description': metadata.series_description,
                    'study_date': metadata.study_date
                }
            }


def create_unet_model(variant: str = 'standard',
                      in_channels: int = 1,
                      out_channels: int = 1,
                      base_features: int = 64) -> 'nn.Module':
    """Factory function to create U-Net model.

    Args:
        variant: 'standard', 'attention', or 'residual'
        in_channels: Number of input channels
        out_channels: Number of output channels
        base_features: Base feature count

    Returns:
        U-Net model instance
    """
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch required for U-Net")

    variant_map = {
        'standard': UNet,
        'attention': AttentionUNet,
        'residual': ResidualUNet
    }

    if variant not in variant_map:
        raise ValueError(f"Unknown variant: {variant}. Use: {list(variant_map.keys())}")

    return variant_map[variant](in_channels, out_channels, base_features)


def check_segmentation_available() -> Dict[str, bool]:
    """Check available segmentation dependencies."""
    return {
        'pytorch': TORCH_AVAILABLE,
        'scipy': SCIPY_AVAILABLE,
        'scikit-image': SKIMAGE_AVAILABLE,
        'gpu': TORCH_AVAILABLE and torch.cuda.is_available() if TORCH_AVAILABLE else False
    }
