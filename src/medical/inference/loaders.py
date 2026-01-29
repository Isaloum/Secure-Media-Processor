"""Model loaders and inference engines for ML models.

This module provides base classes and implementations for loading
and running inference on PyTorch and ONNX models.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Any
from abc import ABC, abstractmethod
import numpy as np

from .config import ModelConfig, PredictionResult, PredictionType, ModelType

logger = logging.getLogger(__name__)

# Optional dependencies
TORCH_AVAILABLE = False
ONNX_AVAILABLE = False
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
    logger.debug("PyTorch available for ML inference")
except ImportError:
    logger.info("PyTorch not installed - ML inference limited")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
    logger.debug("ONNX Runtime available for inference")
except ImportError:
    logger.debug("ONNX Runtime not installed")


class BaseModelInference(ABC):
    """Abstract base class for model inference."""

    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """Load model from path."""
        pass

    @abstractmethod
    def predict(self, image: np.ndarray) -> PredictionResult:
        """Run inference on image."""
        pass

    @abstractmethod
    def predict_batch(self, images: List[np.ndarray]) -> List[PredictionResult]:
        """Run inference on batch of images."""
        pass


class PyTorchInference(BaseModelInference):
    """PyTorch model inference."""

    def __init__(self, config: ModelConfig):
        """Initialize PyTorch inference.

        Args:
            config: Model configuration
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed. Install with: pip install torch")

        self.config = config
        self.model = None
        self.device = None

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

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load PyTorch model.

        Args:
            model_path: Path to model file (.pt, .pth, or TorchScript .pt)
        """
        path = model_path or self.config.model_path
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        if self.config.model_type == ModelType.TORCHSCRIPT:
            self.model = torch.jit.load(str(path), map_location=self.device)
        else:
            # Load state dict - requires model architecture to be defined
            # For flexibility, we try to load as a complete model first
            try:
                self.model = torch.load(str(path), map_location=self.device)
            except Exception:
                raise ValueError(
                    "Could not load model. For state_dict models, provide model architecture. "
                    "For portable models, use TorchScript format."
                )

        self.model.eval()
        logger.info(f"Loaded model from {path}")

    def _preprocess(self, image: np.ndarray) -> Any:
        """Preprocess image for model input.

        Args:
            image: Input image (2D or 3D numpy array)

        Returns:
            Preprocessed tensor
        """
        # Ensure float32
        image = image.astype(np.float32)

        # Add channel dimension if needed
        if image.ndim == 2:
            image = image[np.newaxis, ...]  # (H, W) -> (1, H, W)

        # Add batch dimension if needed
        if image.ndim == 3:
            image = image[np.newaxis, ...]  # (C, H, W) -> (1, C, H, W)

        # Convert to tensor
        tensor = torch.from_numpy(image)

        # Normalize if configured
        if self.config.normalize_input:
            tensor = (tensor - self.config.input_mean) / self.config.input_std

        return tensor.to(self.device)

    def predict(self, image: np.ndarray) -> PredictionResult:
        """Run inference on single image.

        Args:
            image: Input image

        Returns:
            PredictionResult with probabilities and prediction
        """
        if self.model is None:
            self.load_model()

        # Preprocess
        input_tensor = self._preprocess(image)

        # Inference
        with torch.no_grad():
            output = self.model(input_tensor)

            # Handle different output types
            if self.config.prediction_type == PredictionType.BINARY:
                # Sigmoid for binary classification
                probs = torch.sigmoid(output).cpu().numpy().flatten()
                if len(probs) == 1:
                    probs = np.array([1 - probs[0], probs[0]])

            elif self.config.prediction_type == PredictionType.MULTICLASS:
                # Softmax for multiclass
                probs = F.softmax(output, dim=1).cpu().numpy().flatten()

            elif self.config.prediction_type == PredictionType.REGRESSION:
                # Direct output for regression
                probs = output.cpu().numpy().flatten()

            elif self.config.prediction_type == PredictionType.SEGMENTATION:
                # Sigmoid for segmentation mask
                probs = torch.sigmoid(output).cpu().numpy()

            raw_output = output.cpu().numpy()

        # Determine prediction
        if self.config.prediction_type in [PredictionType.BINARY, PredictionType.MULTICLASS]:
            predicted_class = int(np.argmax(probs))
            confidence = float(probs[predicted_class])
            predicted_label = self.config.class_names[predicted_class] if predicted_class < len(self.config.class_names) else f"Class {predicted_class}"
        elif self.config.prediction_type == PredictionType.REGRESSION:
            predicted_class = 0
            confidence = float(probs[0])
            predicted_label = f"Risk Score: {confidence:.3f}"
        else:
            predicted_class = 0
            confidence = 1.0
            predicted_label = "Segmentation"

        return PredictionResult(
            probabilities=probs,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            confidence=confidence,
            raw_output=raw_output,
            metadata={
                'class_names': self.config.class_names,
                'threshold': self.config.threshold,
                'device': str(self.device)
            }
        )

    def predict_batch(self, images: List[np.ndarray]) -> List[PredictionResult]:
        """Run inference on batch of images.

        Args:
            images: List of input images

        Returns:
            List of PredictionResults
        """
        results = []

        # Process in batches
        for i in range(0, len(images), self.config.batch_size):
            batch = images[i:i + self.config.batch_size]

            # Preprocess batch
            tensors = [self._preprocess(img) for img in batch]
            batch_tensor = torch.cat(tensors, dim=0)

            with torch.no_grad():
                outputs = self.model(batch_tensor)

            # Process each output
            for j in range(outputs.shape[0]):
                output = outputs[j:j+1]

                if self.config.prediction_type == PredictionType.BINARY:
                    probs = torch.sigmoid(output).cpu().numpy().flatten()
                    if len(probs) == 1:
                        probs = np.array([1 - probs[0], probs[0]])
                elif self.config.prediction_type == PredictionType.MULTICLASS:
                    probs = F.softmax(output, dim=1).cpu().numpy().flatten()
                else:
                    probs = output.cpu().numpy().flatten()

                predicted_class = int(np.argmax(probs))
                confidence = float(probs[predicted_class])
                predicted_label = self.config.class_names[predicted_class] if predicted_class < len(self.config.class_names) else f"Class {predicted_class}"

                results.append(PredictionResult(
                    probabilities=probs,
                    predicted_class=predicted_class,
                    predicted_label=predicted_label,
                    confidence=confidence,
                    raw_output=output.cpu().numpy(),
                    metadata={'class_names': self.config.class_names}
                ))

        return results

    def generate_heatmap(self,
                         image: np.ndarray,
                         method: str = 'gradcam') -> np.ndarray:
        """Generate attention/activation heatmap.

        Shows which regions the model focuses on for prediction.

        Args:
            image: Input image
            method: Heatmap method ('gradcam', 'guided_gradcam')

        Returns:
            Heatmap array same size as input
        """
        if self.model is None:
            self.load_model()

        if method != 'gradcam':
            logger.warning(f"Method {method} not implemented, using gradcam")

        # Simple gradient-based attention
        input_tensor = self._preprocess(image)
        input_tensor.requires_grad = True

        # Forward pass
        output = self.model(input_tensor)

        # Backward pass for the predicted class
        if self.config.prediction_type in [PredictionType.BINARY, PredictionType.MULTICLASS]:
            target = output.argmax(dim=1)
            loss = output[0, target]
        else:
            loss = output.mean()

        loss.backward()

        # Get gradients
        gradients = input_tensor.grad.cpu().numpy()

        # Average over channels and take absolute value
        heatmap = np.abs(gradients).mean(axis=(0, 1))

        # Normalize to 0-1
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8)

        return heatmap


class ONNXInference(BaseModelInference):
    """ONNX Runtime inference."""

    def __init__(self, config: ModelConfig):
        """Initialize ONNX inference.

        Args:
            config: Model configuration
        """
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime not installed. Install with: pip install onnxruntime")

        self.config = config
        self.session = None
        self.input_name = None
        self.output_names = None

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load ONNX model.

        Args:
            model_path: Path to .onnx model file
        """
        import onnxruntime as ort

        path = model_path or self.config.model_path
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        # Configure session
        providers = ['CPUExecutionProvider']
        if self.config.use_gpu:
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
                logger.info("Using CUDA for ONNX inference")

        self.session = ort.InferenceSession(str(path), providers=providers)

        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [out.name for out in self.session.get_outputs()]

        logger.info(f"Loaded ONNX model from {path}")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input."""
        image = image.astype(np.float32)

        if image.ndim == 2:
            image = image[np.newaxis, np.newaxis, ...]
        elif image.ndim == 3:
            image = image[np.newaxis, ...]

        if self.config.normalize_input:
            image = (image - self.config.input_mean) / self.config.input_std

        return image

    def predict(self, image: np.ndarray) -> PredictionResult:
        """Run inference on single image."""
        if self.session is None:
            self.load_model()

        input_data = self._preprocess(image)
        outputs = self.session.run(self.output_names, {self.input_name: input_data})

        output = outputs[0]

        # Apply activation
        if self.config.prediction_type == PredictionType.BINARY:
            probs = 1 / (1 + np.exp(-output))  # Sigmoid
            probs = probs.flatten()
            if len(probs) == 1:
                probs = np.array([1 - probs[0], probs[0]])
        elif self.config.prediction_type == PredictionType.MULTICLASS:
            exp_output = np.exp(output - np.max(output))
            probs = (exp_output / exp_output.sum()).flatten()
        else:
            probs = output.flatten()

        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])
        predicted_label = self.config.class_names[predicted_class] if predicted_class < len(self.config.class_names) else f"Class {predicted_class}"

        return PredictionResult(
            probabilities=probs,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            confidence=confidence,
            raw_output=output,
            metadata={'class_names': self.config.class_names}
        )

    def predict_batch(self, images: List[np.ndarray]) -> List[PredictionResult]:
        """Run inference on batch of images."""
        return [self.predict(img) for img in images]


class ModelEnsemble:
    """Ensemble of multiple models for improved predictions."""

    def __init__(self, models: List[BaseModelInference], weights: Optional[List[float]] = None):
        """Initialize ensemble.

        Args:
            models: List of model inference objects
            weights: Optional weights for each model
        """
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)

        if len(self.weights) != len(models):
            raise ValueError("Number of weights must match number of models")

    def predict(self, image: np.ndarray) -> PredictionResult:
        """Run ensemble prediction.

        Args:
            image: Input image

        Returns:
            Aggregated prediction result
        """
        all_probs = []

        for model, weight in zip(self.models, self.weights):
            result = model.predict(image)
            all_probs.append(result.probabilities * weight)

        # Weighted average of probabilities
        ensemble_probs = np.sum(all_probs, axis=0)
        ensemble_probs = ensemble_probs / ensemble_probs.sum()

        predicted_class = int(np.argmax(ensemble_probs))
        confidence = float(ensemble_probs[predicted_class])

        # Get class names from first model
        class_names = self.models[0].config.class_names if hasattr(self.models[0], 'config') else []
        predicted_label = class_names[predicted_class] if predicted_class < len(class_names) else f"Class {predicted_class}"

        return PredictionResult(
            probabilities=ensemble_probs,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            confidence=confidence,
            raw_output=ensemble_probs,
            metadata={
                'ensemble_size': len(self.models),
                'weights': self.weights
            }
        )
