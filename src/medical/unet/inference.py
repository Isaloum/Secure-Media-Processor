"""U-Net Segmentation Inference Pipeline.

This module provides the main inference pipeline for U-Net segmentation:
- Model loading and management
- Preprocessing
- Single image and volume segmentation
- DICOM integration
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
import numpy as np

from .config import SegmentationConfig, SegmentationResult, UNetVariant
from .models import UNet, AttentionUNet, ResidualUNet, TORCH_AVAILABLE
from .postprocessing import SegmentationPostProcessor

if TORCH_AVAILABLE:
    import torch

logger = logging.getLogger(__name__)

# Check for scipy
SCIPY_AVAILABLE = False
try:
    import scipy.ndimage as ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    pass


class UNetSegmentation:
    """U-Net segmentation inference pipeline.

    Provides end-to-end segmentation from image to processed mask
    with support for preprocessing, inference, and post-processing.

    Example:
        >>> config = SegmentationConfig(variant=UNetVariant.ATTENTION)
        >>> pipeline = UNetSegmentation(config)
        >>> pipeline.load_model('model.pt')
        >>> result = pipeline.segment(image)
        >>> print(f"Found {result.num_regions} regions")
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

    def _preprocess(self, image: np.ndarray) -> 'torch.Tensor':
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


def check_segmentation_available() -> Dict[str, bool]:
    """Check available segmentation dependencies."""
    return {
        'pytorch': TORCH_AVAILABLE,
        'scipy': SCIPY_AVAILABLE,
        'scikit-image': False,  # Will be checked dynamically
        'gpu': TORCH_AVAILABLE and torch.cuda.is_available() if TORCH_AVAILABLE else False
    }
