"""ML Inference package for medical image analysis.

This package provides ML inference capabilities:
- pipeline: Main inference pipeline for cancer prediction
- Model loading for PyTorch and ONNX models
- Batch processing and ensembles

Example:
    >>> from src.medical.inference import CancerPredictionPipeline, ModelConfig
    >>> config = ModelConfig(model_path='model.pt')
    >>> pipeline = CancerPredictionPipeline(config)
    >>> result = pipeline.predict(image)
"""

from .pipeline import (
    # Enums
    ModelType,
    PredictionType,
    # Config
    ModelConfig,
    PredictionResult,
    # Inference classes
    BaseModelInference,
    PyTorchInference,
    ONNXInference,
    # Pipeline
    CancerPredictionPipeline,
    ModelEnsemble,
    # Availability checks
    TORCH_AVAILABLE,
    ONNX_AVAILABLE,
)

__all__ = [
    # Enums
    'ModelType',
    'PredictionType',
    # Config
    'ModelConfig',
    'PredictionResult',
    # Inference
    'BaseModelInference',
    'PyTorchInference',
    'ONNXInference',
    # Pipeline
    'CancerPredictionPipeline',
    'ModelEnsemble',
    # Flags
    'TORCH_AVAILABLE',
    'ONNX_AVAILABLE',
]
