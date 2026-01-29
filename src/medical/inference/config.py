"""Configuration classes for ML inference.

This module defines configuration dataclasses and enums for
model inference settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple


class ModelType(Enum):
    """Supported model types."""
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TORCHSCRIPT = "torchscript"


class PredictionType(Enum):
    """Types of predictions."""
    BINARY = "binary"  # Cancer / No Cancer
    MULTICLASS = "multiclass"  # Multiple stages/types
    REGRESSION = "regression"  # Risk score
    SEGMENTATION = "segmentation"  # Tumor segmentation


@dataclass
class ModelConfig:
    """Configuration for ML model."""
    model_path: str
    model_type: ModelType = ModelType.PYTORCH
    prediction_type: PredictionType = PredictionType.BINARY

    # Input configuration
    input_shape: Tuple[int, ...] = (1, 1, 224, 224)  # (batch, channels, height, width)
    input_channels: int = 1
    normalize_input: bool = True
    input_mean: float = 0.0
    input_std: float = 1.0

    # Output configuration
    num_classes: int = 2
    class_names: List[str] = field(default_factory=lambda: ["No Cancer", "Cancer"])
    threshold: float = 0.5

    # Processing
    use_gpu: bool = True
    batch_size: int = 1


@dataclass
class PredictionResult:
    """Result of model prediction."""
    import numpy as np
    from typing import Dict, Any, Optional

    # Probabilities for each class
    probabilities: 'np.ndarray'

    # Predicted class index
    predicted_class: int

    # Predicted class name
    predicted_label: str

    # Confidence score
    confidence: float

    # Raw model output
    raw_output: 'np.ndarray'

    # Optional heatmap/attention map
    heatmap: 'Optional[np.ndarray]' = None

    # Additional metadata
    metadata: 'Dict[str, Any]' = field(default_factory=dict)

    def to_dict(self) -> 'Dict[str, Any]':
        """Convert to dictionary for JSON serialization."""
        return {
            'predicted_class': self.predicted_class,
            'predicted_label': self.predicted_label,
            'confidence': float(self.confidence),
            'probabilities': {
                name: float(prob)
                for name, prob in zip(
                    self.metadata.get('class_names', [f'class_{i}' for i in range(len(self.probabilities))]),
                    self.probabilities
                )
            },
            'metadata': self.metadata
        }


def check_ml_available() -> dict:
    """Check available ML backends.

    Returns:
        Dictionary with availability status for pytorch, onnx, and gpu.
    """
    result = {
        'pytorch': False,
        'onnx': False,
        'gpu': False
    }

    try:
        import torch
        result['pytorch'] = True
        result['gpu'] = torch.cuda.is_available()
    except ImportError:
        pass

    try:
        import onnxruntime
        result['onnx'] = True
    except ImportError:
        pass

    return result
