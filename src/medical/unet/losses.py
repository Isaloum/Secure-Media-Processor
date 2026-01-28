"""Loss Functions for U-Net Segmentation Training.

This module provides loss functions optimized for medical image segmentation:
- DiceLoss: Dice coefficient based loss
- BCEDiceLoss: Combined BCE and Dice loss
- FocalLoss: For handling class imbalance
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Optional dependencies
TORCH_AVAILABLE = False
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
except ImportError:
    logger.debug("PyTorch not installed - loss functions unavailable")


if TORCH_AVAILABLE:

    class DiceLoss(nn.Module):
        """Dice loss for segmentation training.

        Dice Loss = 1 - Dice Coefficient

        The Dice coefficient measures overlap between predicted and target masks.
        """

        def __init__(self, smooth: float = 1.0):
            """Initialize Dice loss.

            Args:
                smooth: Smoothing factor to avoid division by zero
            """
            super().__init__()
            self.smooth = smooth

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            """Calculate Dice loss.

            Args:
                predictions: Model output logits
                targets: Ground truth binary mask

            Returns:
                Dice loss value
            """
            predictions = torch.sigmoid(predictions)
            predictions = predictions.view(-1)
            targets = targets.view(-1)

            intersection = (predictions * targets).sum()
            dice = (2. * intersection + self.smooth) / (predictions.sum() + targets.sum() + self.smooth)

            return 1 - dice


    class BCEDiceLoss(nn.Module):
        """Combined Binary Cross-Entropy and Dice loss.

        This combination often provides better training stability than
        either loss alone for segmentation tasks.
        """

        def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5):
            """Initialize combined loss.

            Args:
                bce_weight: Weight for BCE component
                dice_weight: Weight for Dice component
            """
            super().__init__()
            self.bce_weight = bce_weight
            self.dice_weight = dice_weight
            self.bce = nn.BCEWithLogitsLoss()
            self.dice = DiceLoss()

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            """Calculate combined loss.

            Args:
                predictions: Model output logits
                targets: Ground truth binary mask

            Returns:
                Combined loss value
            """
            bce_loss = self.bce(predictions, targets)
            dice_loss = self.dice(predictions, targets)
            return self.bce_weight * bce_loss + self.dice_weight * dice_loss


    class FocalLoss(nn.Module):
        """Focal loss for handling class imbalance.

        Focal Loss = -alpha * (1 - pt)^gamma * log(pt)

        Reference: Lin et al., "Focal Loss for Dense Object Detection" (2017)
        """

        def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
            """Initialize Focal loss.

            Args:
                alpha: Weighting factor for positive class
                gamma: Focusing parameter (higher = more focus on hard examples)
            """
            super().__init__()
            self.alpha = alpha
            self.gamma = gamma

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            """Calculate Focal loss.

            Args:
                predictions: Model output logits
                targets: Ground truth binary mask

            Returns:
                Focal loss value
            """
            bce = F.binary_cross_entropy_with_logits(predictions, targets, reduction='none')
            pt = torch.exp(-bce)
            focal_loss = self.alpha * (1 - pt) ** self.gamma * bce
            return focal_loss.mean()


    class TverskyLoss(nn.Module):
        """Tversky loss for handling precision/recall trade-off.

        Tversky index generalizes Dice coefficient with alpha and beta parameters
        to weight false positives and false negatives differently.
        """

        def __init__(self, alpha: float = 0.7, beta: float = 0.3, smooth: float = 1.0):
            """Initialize Tversky loss.

            Args:
                alpha: Weight for false positives
                beta: Weight for false negatives
                smooth: Smoothing factor
            """
            super().__init__()
            self.alpha = alpha
            self.beta = beta
            self.smooth = smooth

        def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            """Calculate Tversky loss."""
            predictions = torch.sigmoid(predictions)
            predictions = predictions.view(-1)
            targets = targets.view(-1)

            tp = (predictions * targets).sum()
            fp = ((1 - targets) * predictions).sum()
            fn = (targets * (1 - predictions)).sum()

            tversky = (tp + self.smooth) / (tp + self.alpha * fp + self.beta * fn + self.smooth)

            return 1 - tversky
