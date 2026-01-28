"""U-Net Architecture Models for Medical Image Segmentation.

This module provides U-Net architectures including:
- Standard U-Net encoder-decoder
- Attention U-Net with attention gates
- Residual U-Net with skip connections

These models are designed for tumor/lesion segmentation in medical images.
"""

from __future__ import annotations

import logging
from typing import Optional
from enum import Enum

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
    logger.debug("PyTorch available for U-Net models")
except ImportError:
    logger.info("PyTorch not installed - U-Net models unavailable")


class UNetVariant(Enum):
    """U-Net architecture variants."""
    STANDARD = "standard"
    ATTENTION = "attention"
    RESIDUAL = "residual"


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
