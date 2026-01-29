"""ML Inference package for Medical Image Analysis.

This package provides a framework for running trained ML models
on medical images, particularly for cancer prediction from MRI.

Modules:
    config: Configuration classes and enums
    loaders: Model loading and inference engines
    pipeline: End-to-end prediction pipelines

Features:
    - Load PyTorch/ONNX models
    - GPU-accelerated inference
    - Batch processing
    - Probability outputs and heatmaps
    - Model ensemble support

Example:
    >>> from src.medical.inference import CancerPredictionPipeline, ModelConfig
    >>> config = ModelConfig(model_path='model.pt')
    >>> pipeline = CancerPredictionPipeline(config)
    >>> result = pipeline.predict_single(image)
"""

from .config import (
    ModelType,
    PredictionType,
    ModelConfig,
    PredictionResult,
    check_ml_available,
)

from .loaders import (
    BaseModelInference,
    PyTorchInference,
    ONNXInference,
    ModelEnsemble,
    TORCH_AVAILABLE,
    ONNX_AVAILABLE,
)

from .pipeline import (
    CancerPredictionPipeline,
)

__all__ = [
    # Config
    'ModelType',
    'PredictionType',
    'ModelConfig',
    'PredictionResult',
    'check_ml_available',
    # Loaders
    'BaseModelInference',
    'PyTorchInference',
    'ONNXInference',
    'ModelEnsemble',
    'TORCH_AVAILABLE',
    'ONNX_AVAILABLE',
    # Pipeline
    'CancerPredictionPipeline',
]
