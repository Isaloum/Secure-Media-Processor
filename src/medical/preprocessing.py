"""Medical image preprocessing pipeline for MRI analysis.

This module provides specialized preprocessing for medical imaging,
particularly MRI breast cancer analysis workflows.

Features:
- N4 Bias Field Correction
- Intensity normalization (histogram matching, z-score)
- Noise reduction (non-local means, gaussian)
- Contrast enhancement
- Breast region segmentation
- Standard preprocessing pipelines
"""

import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

# Optional dependencies
SCIPY_AVAILABLE = False
SKIMAGE_AVAILABLE = False
CV2_AVAILABLE = False

try:
    import scipy.ndimage as ndimage
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    logger.debug("scipy not installed - some preprocessing features disabled")

try:
    from skimage import exposure, filters, morphology, measure
    from skimage.restoration import denoise_nl_means, estimate_sigma
    SKIMAGE_AVAILABLE = True
except ImportError:
    logger.debug("scikit-image not installed - some preprocessing features disabled")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    logger.debug("opencv not installed - some preprocessing features disabled")


class NormalizationMethod(Enum):
    """Normalization methods for medical images."""
    MINMAX = "minmax"
    ZSCORE = "zscore"
    HISTOGRAM = "histogram"
    PERCENTILE = "percentile"
    NYUL = "nyul"  # Nyul histogram standardization


class NoiseReductionMethod(Enum):
    """Noise reduction methods."""
    GAUSSIAN = "gaussian"
    MEDIAN = "median"
    BILATERAL = "bilateral"
    NLM = "nlm"  # Non-local means
    ANISOTROPIC = "anisotropic"


@dataclass
class PreprocessingConfig:
    """Configuration for preprocessing pipeline."""

    # Normalization
    normalize: bool = True
    normalization_method: NormalizationMethod = NormalizationMethod.ZSCORE
    percentile_low: float = 1.0
    percentile_high: float = 99.0

    # Noise reduction
    denoise: bool = True
    denoise_method: NoiseReductionMethod = NoiseReductionMethod.NLM
    denoise_strength: float = 1.0

    # Bias field correction
    bias_correction: bool = True
    bias_iterations: int = 50

    # Contrast enhancement
    enhance_contrast: bool = False
    clahe_clip_limit: float = 2.0

    # Resampling
    resample: bool = False
    target_spacing: Optional[Tuple[float, float, float]] = None

    # Intensity windowing
    window_center: Optional[float] = None
    window_width: Optional[float] = None


@dataclass
class PreprocessingResult:
    """Result of preprocessing operation."""
    data: np.ndarray
    original_shape: Tuple[int, ...]
    final_shape: Tuple[int, ...]
    steps_applied: List[str]
    metadata: Dict[str, Any]


class MedicalImagePreprocessor:
    """Preprocess medical images for ML analysis.

    Provides standardized preprocessing pipelines commonly used
    in medical imaging research, particularly for MRI analysis.
    """

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        """Initialize preprocessor with configuration.

        Args:
            config: Preprocessing configuration. Uses defaults if None.
        """
        self.config = config or PreprocessingConfig()
        self._check_dependencies()

    def _check_dependencies(self):
        """Check and log available dependencies."""
        deps = {
            'scipy': SCIPY_AVAILABLE,
            'scikit-image': SKIMAGE_AVAILABLE,
            'opencv': CV2_AVAILABLE
        }
        missing = [k for k, v in deps.items() if not v]
        if missing:
            logger.warning(f"Missing optional dependencies: {missing}. Some features may be limited.")

    def preprocess(self,
                   image: np.ndarray,
                   config: Optional[PreprocessingConfig] = None) -> PreprocessingResult:
        """Apply full preprocessing pipeline.

        Args:
            image: Input image (2D or 3D numpy array)
            config: Optional override configuration

        Returns:
            PreprocessingResult with processed image and metadata
        """
        cfg = config or self.config
        steps_applied = []
        metadata = {'original_dtype': str(image.dtype)}

        # Convert to float32 for processing
        result = image.astype(np.float32)
        original_shape = result.shape

        # 1. Bias field correction (for MRI)
        if cfg.bias_correction:
            result = self.correct_bias_field(result, iterations=cfg.bias_iterations)
            steps_applied.append('bias_correction')

        # 2. Intensity windowing
        if cfg.window_center is not None and cfg.window_width is not None:
            result = self.apply_window(result, cfg.window_center, cfg.window_width)
            steps_applied.append('windowing')

        # 3. Noise reduction
        if cfg.denoise:
            result = self.reduce_noise(result, method=cfg.denoise_method, strength=cfg.denoise_strength)
            steps_applied.append(f'denoise_{cfg.denoise_method.value}')

        # 4. Normalization
        if cfg.normalize:
            result = self.normalize(result, method=cfg.normalization_method,
                                    percentile_low=cfg.percentile_low,
                                    percentile_high=cfg.percentile_high)
            steps_applied.append(f'normalize_{cfg.normalization_method.value}')

        # 5. Contrast enhancement
        if cfg.enhance_contrast:
            result = self.enhance_contrast_clahe(result, clip_limit=cfg.clahe_clip_limit)
            steps_applied.append('clahe')

        # 6. Resampling
        if cfg.resample and cfg.target_spacing is not None:
            # Would need voxel spacing info from DICOM
            steps_applied.append('resample')

        return PreprocessingResult(
            data=result,
            original_shape=original_shape,
            final_shape=result.shape,
            steps_applied=steps_applied,
            metadata=metadata
        )

    def normalize(self,
                  image: np.ndarray,
                  method: NormalizationMethod = NormalizationMethod.ZSCORE,
                  percentile_low: float = 1.0,
                  percentile_high: float = 99.0) -> np.ndarray:
        """Normalize image intensities.

        Args:
            image: Input image
            method: Normalization method to use
            percentile_low: Lower percentile for clipping
            percentile_high: Upper percentile for clipping

        Returns:
            Normalized image
        """
        if method == NormalizationMethod.MINMAX:
            min_val = image.min()
            max_val = image.max()
            if max_val > min_val:
                return (image - min_val) / (max_val - min_val)
            return image - min_val

        elif method == NormalizationMethod.ZSCORE:
            # Exclude background (zeros) from statistics
            mask = image > 0
            if mask.any():
                mean = image[mask].mean()
                std = image[mask].std()
                if std > 0:
                    return (image - mean) / std
                return image - mean
            return image

        elif method == NormalizationMethod.PERCENTILE:
            p_low = np.percentile(image, percentile_low)
            p_high = np.percentile(image, percentile_high)
            clipped = np.clip(image, p_low, p_high)
            if p_high > p_low:
                return (clipped - p_low) / (p_high - p_low)
            return clipped - p_low

        elif method == NormalizationMethod.HISTOGRAM:
            if SKIMAGE_AVAILABLE:
                return exposure.equalize_hist(image)
            else:
                logger.warning("scikit-image not available, falling back to minmax")
                return self.normalize(image, NormalizationMethod.MINMAX)

        return image

    def reduce_noise(self,
                     image: np.ndarray,
                     method: NoiseReductionMethod = NoiseReductionMethod.NLM,
                     strength: float = 1.0) -> np.ndarray:
        """Reduce noise in medical image.

        Args:
            image: Input image
            method: Noise reduction method
            strength: Strength of noise reduction (0.5-2.0 typical)

        Returns:
            Denoised image
        """
        if method == NoiseReductionMethod.GAUSSIAN:
            if SCIPY_AVAILABLE:
                sigma = strength * 1.0
                return ndimage.gaussian_filter(image, sigma=sigma)
            elif CV2_AVAILABLE:
                ksize = int(strength * 3) | 1  # Ensure odd
                return cv2.GaussianBlur(image, (ksize, ksize), 0)

        elif method == NoiseReductionMethod.MEDIAN:
            if SCIPY_AVAILABLE:
                size = int(strength * 3) | 1
                return ndimage.median_filter(image, size=size)
            elif CV2_AVAILABLE:
                ksize = int(strength * 3) | 1
                return cv2.medianBlur(image.astype(np.float32), ksize)

        elif method == NoiseReductionMethod.BILATERAL:
            if CV2_AVAILABLE:
                d = int(strength * 5)
                sigma_color = strength * 75
                sigma_space = strength * 75
                return cv2.bilateralFilter(image.astype(np.float32), d, sigma_color, sigma_space)

        elif method == NoiseReductionMethod.NLM:
            if SKIMAGE_AVAILABLE:
                # Estimate noise level
                sigma_est = estimate_sigma(image)
                # Apply non-local means
                h = strength * sigma_est
                return denoise_nl_means(image, h=h, fast_mode=True,
                                        patch_size=5, patch_distance=6)
            else:
                logger.warning("scikit-image not available for NLM, using gaussian")
                return self.reduce_noise(image, NoiseReductionMethod.GAUSSIAN, strength)

        elif method == NoiseReductionMethod.ANISOTROPIC:
            # Anisotropic diffusion (edge-preserving smoothing)
            return self._anisotropic_diffusion(image, niter=int(strength * 10))

        return image

    def _anisotropic_diffusion(self,
                               image: np.ndarray,
                               niter: int = 10,
                               kappa: float = 50,
                               gamma: float = 0.1) -> np.ndarray:
        """Apply anisotropic diffusion filter.

        Preserves edges while smoothing homogeneous regions.
        Based on Perona-Malik diffusion.
        """
        result = image.astype(np.float64)

        for _ in range(niter):
            # Calculate gradients
            if SCIPY_AVAILABLE:
                grad_n = np.roll(result, -1, axis=0) - result
                grad_s = np.roll(result, 1, axis=0) - result
                grad_e = np.roll(result, -1, axis=1) - result
                grad_w = np.roll(result, 1, axis=1) - result

                # Diffusion coefficients (Perona-Malik)
                c_n = np.exp(-(grad_n / kappa) ** 2)
                c_s = np.exp(-(grad_s / kappa) ** 2)
                c_e = np.exp(-(grad_e / kappa) ** 2)
                c_w = np.exp(-(grad_w / kappa) ** 2)

                # Update
                result += gamma * (c_n * grad_n + c_s * grad_s + c_e * grad_e + c_w * grad_w)

        return result.astype(np.float32)

    def correct_bias_field(self,
                           image: np.ndarray,
                           iterations: int = 50,
                           convergence_threshold: float = 0.001) -> np.ndarray:
        """Correct MRI bias field inhomogeneity.

        Simplified N4-like bias field correction.
        For production, consider using SimpleITK's N4BiasFieldCorrection.

        Args:
            image: Input MRI image
            iterations: Number of iterations
            convergence_threshold: Convergence threshold

        Returns:
            Bias-corrected image
        """
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available for bias correction")
            return image

        # Create mask of tissue (non-background)
        mask = image > np.percentile(image[image > 0], 10) if (image > 0).any() else image > 0

        if not mask.any():
            return image

        result = image.copy().astype(np.float64)
        result[result == 0] = 1e-10  # Avoid log(0)

        # Iterative bias field estimation
        log_image = np.log(result)

        for i in range(iterations):
            # Estimate bias field as low-frequency component
            bias_field = ndimage.gaussian_filter(log_image, sigma=30)

            # Subtract bias field in log domain
            corrected_log = log_image - bias_field

            # Check convergence
            if i > 0:
                change = np.abs(corrected_log - prev_log).mean()
                if change < convergence_threshold:
                    break

            prev_log = corrected_log.copy()
            log_image = corrected_log

        # Convert back from log domain
        corrected = np.exp(corrected_log)

        # Restore background
        corrected[~mask] = image[~mask]

        return corrected.astype(np.float32)

    def apply_window(self,
                     image: np.ndarray,
                     center: float,
                     width: float) -> np.ndarray:
        """Apply intensity windowing (window/level).

        Common in CT and MRI visualization.

        Args:
            image: Input image
            center: Window center (level)
            width: Window width

        Returns:
            Windowed image
        """
        min_val = center - width / 2
        max_val = center + width / 2
        windowed = np.clip(image, min_val, max_val)
        # Normalize to 0-1
        return (windowed - min_val) / width

    def enhance_contrast_clahe(self,
                               image: np.ndarray,
                               clip_limit: float = 2.0,
                               tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input image (2D)
            clip_limit: Contrast limit
            tile_grid_size: Size of grid for histogram equalization

        Returns:
            Contrast-enhanced image
        """
        if CV2_AVAILABLE:
            # Normalize to 0-255 for CLAHE
            normalized = ((image - image.min()) / (image.max() - image.min() + 1e-10) * 255).astype(np.uint8)

            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            enhanced = clahe.apply(normalized)

            return enhanced.astype(np.float32) / 255.0

        elif SKIMAGE_AVAILABLE:
            return exposure.equalize_adapthist(image, clip_limit=clip_limit / 10)

        logger.warning("No CLAHE implementation available")
        return image

    def resample_volume(self,
                        volume: np.ndarray,
                        current_spacing: Tuple[float, float, float],
                        target_spacing: Tuple[float, float, float],
                        order: int = 1) -> np.ndarray:
        """Resample volume to target voxel spacing.

        Args:
            volume: Input 3D volume
            current_spacing: Current voxel spacing (z, y, x)
            target_spacing: Target voxel spacing (z, y, x)
            order: Interpolation order (0=nearest, 1=linear, 3=cubic)

        Returns:
            Resampled volume
        """
        if not SCIPY_AVAILABLE:
            raise RuntimeError("scipy required for resampling")

        # Calculate zoom factors
        zoom_factors = tuple(c / t for c, t in zip(current_spacing, target_spacing))

        return ndimage.zoom(volume, zoom_factors, order=order)

    def extract_breast_region(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract breast region from MRI slice.

        Simple breast segmentation for preprocessing.
        For production, use trained segmentation models.

        Args:
            image: Input breast MRI slice

        Returns:
            Tuple of (segmented_image, mask)
        """
        if not (SCIPY_AVAILABLE or CV2_AVAILABLE):
            logger.warning("scipy or opencv required for segmentation")
            return image, np.ones_like(image, dtype=bool)

        # Threshold to separate tissue from background
        threshold = np.percentile(image[image > 0], 10) if (image > 0).any() else 0
        mask = image > threshold

        if SCIPY_AVAILABLE:
            # Fill holes
            mask = ndimage.binary_fill_holes(mask)

            # Remove small objects
            labeled, num_features = ndimage.label(mask)
            if num_features > 1:
                sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
                largest = np.argmax(sizes) + 1
                mask = labeled == largest

        elif CV2_AVAILABLE:
            mask = mask.astype(np.uint8)
            # Morphological operations
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = mask.astype(bool)

        # Apply mask
        segmented = image.copy()
        segmented[~mask] = 0

        return segmented, mask


class BreastMRIPreprocessor(MedicalImagePreprocessor):
    """Specialized preprocessor for breast MRI analysis.

    Implements preprocessing pipeline optimized for breast cancer
    detection and prediction from MRI images.
    """

    def __init__(self):
        """Initialize with breast MRI optimized settings."""
        config = PreprocessingConfig(
            normalize=True,
            normalization_method=NormalizationMethod.PERCENTILE,
            percentile_low=1.0,
            percentile_high=99.0,
            denoise=True,
            denoise_method=NoiseReductionMethod.NLM,
            denoise_strength=0.8,
            bias_correction=True,
            bias_iterations=50,
            enhance_contrast=True,
            clahe_clip_limit=2.0
        )
        super().__init__(config)

    def preprocess_for_prediction(self,
                                   volume: np.ndarray,
                                   target_shape: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Preprocess breast MRI volume for cancer prediction model.

        Applies standardized preprocessing pipeline:
        1. Bias field correction
        2. Noise reduction
        3. Intensity normalization
        4. Optional resizing

        Args:
            volume: Input 3D MRI volume
            target_shape: Optional target shape for model input

        Returns:
            Preprocessed volume ready for model inference
        """
        # Process each slice
        processed_slices = []

        for i in range(volume.shape[0]):
            slice_2d = volume[i]

            # Apply preprocessing pipeline
            result = self.preprocess(slice_2d)
            processed_slices.append(result.data)

        processed_volume = np.stack(processed_slices, axis=0)

        # Resize if target shape specified
        if target_shape is not None and SCIPY_AVAILABLE:
            zoom_factors = tuple(t / c for t, c in zip(target_shape, processed_volume.shape))
            processed_volume = ndimage.zoom(processed_volume, zoom_factors, order=1)

        return processed_volume

    def extract_features(self, image: np.ndarray) -> Dict[str, float]:
        """Extract basic radiomics-like features from image.

        For full radiomics, consider using pyradiomics library.

        Args:
            image: Input image

        Returns:
            Dictionary of extracted features
        """
        # Mask non-zero region
        mask = image > 0
        if not mask.any():
            return {}

        values = image[mask]

        features = {
            # First-order statistics
            'mean': float(values.mean()),
            'std': float(values.std()),
            'min': float(values.min()),
            'max': float(values.max()),
            'median': float(np.median(values)),
            'skewness': float(self._skewness(values)),
            'kurtosis': float(self._kurtosis(values)),
            'energy': float(np.sum(values ** 2)),
            'entropy': float(self._entropy(values)),

            # Shape features
            'volume': int(mask.sum()),
        }

        return features

    def _skewness(self, values: np.ndarray) -> float:
        """Calculate skewness."""
        n = len(values)
        if n < 3:
            return 0.0
        mean = values.mean()
        std = values.std()
        if std == 0:
            return 0.0
        return ((values - mean) ** 3).mean() / (std ** 3)

    def _kurtosis(self, values: np.ndarray) -> float:
        """Calculate kurtosis."""
        n = len(values)
        if n < 4:
            return 0.0
        mean = values.mean()
        std = values.std()
        if std == 0:
            return 0.0
        return ((values - mean) ** 4).mean() / (std ** 4) - 3

    def _entropy(self, values: np.ndarray, bins: int = 64) -> float:
        """Calculate image entropy."""
        hist, _ = np.histogram(values, bins=bins)
        hist = hist / hist.sum()
        hist = hist[hist > 0]  # Remove zeros
        return -np.sum(hist * np.log2(hist))
