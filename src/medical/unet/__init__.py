"""U-Net Segmentation Module for Medical Image Analysis.

This package provides U-Net-based segmentation for tumor/lesion detection:

Modules:
- models: U-Net architectures (Standard, Attention, Residual)
- losses: Training loss functions (Dice, BCE+Dice, Focal)
- metrics: Evaluation metrics (Dice, IoU, Hausdorff)
- postprocessing: Mask post-processing utilities
- inference: Segmentation pipeline

Example:
    >>> from src.medical.unet import UNetSegmentation, SegmentationConfig
    >>> config = SegmentationConfig(variant=UNetVariant.ATTENTION)
    >>> pipeline = UNetSegmentation(config)
    >>> result = pipeline.segment(image)
"""

from .config import (
    UNetVariant,
    SegmentationConfig,
    SegmentationResult,
)

from .models import (
    TORCH_AVAILABLE,
    create_unet_model,
)

from .metrics import SegmentationMetrics

from .postprocessing import SegmentationPostProcessor

from .inference import (
    UNetSegmentation,
    check_segmentation_available,
)

# Conditional exports based on PyTorch availability
if TORCH_AVAILABLE:
    from .models import (
        DoubleConv,
        Down,
        Up,
        AttentionGate,
        UNet,
        AttentionUNet,
        ResidualUNet,
        ResidualDoubleConv,
    )
    from .losses import (
        DiceLoss,
        BCEDiceLoss,
        FocalLoss,
        TverskyLoss,
    )

__all__ = [
    # Config
    'UNetVariant',
    'SegmentationConfig',
    'SegmentationResult',
    # Models
    'TORCH_AVAILABLE',
    'create_unet_model',
    'UNet',
    'AttentionUNet',
    'ResidualUNet',
    # Losses
    'DiceLoss',
    'BCEDiceLoss',
    'FocalLoss',
    'TverskyLoss',
    # Metrics
    'SegmentationMetrics',
    # Post-processing
    'SegmentationPostProcessor',
    # Inference
    'UNetSegmentation',
    'check_segmentation_available',
]
