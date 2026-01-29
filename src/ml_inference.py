"""ML Inference Pipeline for Medical Image Analysis.

This module is maintained for backward compatibility.
New code should import from src.medical.inference instead.
"""

# Re-export from new location for backward compatibility
from src.medical.inference import (
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
    check_ml_available,
)

__all__ = [
    'ModelType',
    'PredictionType',
    'ModelConfig',
    'PredictionResult',
    'BaseModelInference',
    'PyTorchInference',
    'ONNXInference',
    'CancerPredictionPipeline',
    'ModelEnsemble',
    'TORCH_AVAILABLE',
    'ONNX_AVAILABLE',
    'check_ml_available',
]
