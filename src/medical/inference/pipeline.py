"""Cancer Prediction Pipeline for Medical Image Analysis.

This module provides end-to-end pipelines for cancer prediction
from MRI images, combining preprocessing, inference, and reporting.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union, Dict, Any
import numpy as np

from .config import ModelConfig, ModelType, PredictionType
from .loaders import PyTorchInference, ONNXInference

logger = logging.getLogger(__name__)


class CancerPredictionPipeline:
    """End-to-end pipeline for cancer prediction from MRI.

    Combines preprocessing, inference, and result interpretation.
    """

    def __init__(self,
                 model_config: ModelConfig,
                 use_preprocessing: bool = True):
        """Initialize cancer prediction pipeline.

        Args:
            model_config: Configuration for the ML model
            use_preprocessing: Whether to apply medical preprocessing
        """
        self.model_config = model_config
        self.use_preprocessing = use_preprocessing

        # Initialize inference engine
        if model_config.model_type == ModelType.ONNX:
            self.inference = ONNXInference(model_config)
        else:
            self.inference = PyTorchInference(model_config)

        # Initialize preprocessor
        if use_preprocessing:
            from src.medical_preprocessing import BreastMRIPreprocessor
            self.preprocessor = BreastMRIPreprocessor()
        else:
            self.preprocessor = None

    def predict_single(self,
                       image: np.ndarray,
                       generate_heatmap: bool = False) -> Dict[str, Any]:
        """Predict cancer probability for single image.

        Args:
            image: Input MRI image (2D slice or preprocessed)
            generate_heatmap: Whether to generate attention heatmap

        Returns:
            Dictionary with prediction results
        """
        # Preprocess if enabled
        if self.preprocessor is not None:
            result = self.preprocessor.preprocess(image)
            processed_image = result.data
        else:
            processed_image = image

        # Run inference
        prediction = self.inference.predict(processed_image)

        # Generate heatmap if requested
        heatmap = None
        if generate_heatmap and isinstance(self.inference, PyTorchInference):
            heatmap = self.inference.generate_heatmap(processed_image)

        return {
            'prediction': prediction.to_dict(),
            'heatmap': heatmap,
            'preprocessed': self.preprocessor is not None
        }

    def predict_volume(self,
                       volume: np.ndarray,
                       aggregate: str = 'max') -> Dict[str, Any]:
        """Predict cancer probability for 3D MRI volume.

        Processes each slice and aggregates results.

        Args:
            volume: 3D MRI volume (slices, height, width)
            aggregate: Aggregation method ('max', 'mean', 'voting')

        Returns:
            Dictionary with aggregated prediction
        """
        slice_predictions = []

        for i in range(volume.shape[0]):
            slice_2d = volume[i]
            result = self.predict_single(slice_2d)
            slice_predictions.append(result['prediction'])

        # Aggregate predictions
        all_probs = np.array([p['probabilities']['Cancer'] for p in slice_predictions])

        if aggregate == 'max':
            final_prob = float(all_probs.max())
            most_suspicious_slice = int(all_probs.argmax())
        elif aggregate == 'mean':
            final_prob = float(all_probs.mean())
            most_suspicious_slice = int(all_probs.argmax())
        elif aggregate == 'voting':
            # Majority voting with threshold
            votes = (all_probs > self.model_config.threshold).sum()
            final_prob = float(votes / len(all_probs))
            most_suspicious_slice = int(all_probs.argmax())
        else:
            final_prob = float(all_probs.max())
            most_suspicious_slice = int(all_probs.argmax())

        return {
            'final_probability': final_prob,
            'predicted_label': 'Cancer' if final_prob > self.model_config.threshold else 'No Cancer',
            'confidence': final_prob if final_prob > 0.5 else 1 - final_prob,
            'most_suspicious_slice': most_suspicious_slice,
            'slice_probabilities': all_probs.tolist(),
            'num_slices': volume.shape[0],
            'aggregation_method': aggregate
        }

    def predict_from_dicom(self,
                           dicom_path: Union[str, Path],
                           generate_report: bool = True) -> Dict[str, Any]:
        """Predict from DICOM file or directory.

        Args:
            dicom_path: Path to DICOM file or directory
            generate_report: Whether to generate text report

        Returns:
            Prediction results with optional report
        """
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()
        dicom_path = Path(dicom_path)

        if dicom_path.is_dir():
            # Process as series
            volume = processor.read_dicom_series(dicom_path)
            metadata = volume.slice_metadata[0]
            result = self.predict_volume(volume.pixel_data)
        else:
            # Process single file
            pixel_array, metadata = processor.read_dicom(dicom_path)
            if pixel_array.ndim == 3:
                result = self.predict_volume(pixel_array)
            else:
                single_result = self.predict_single(pixel_array)
                result = {
                    'final_probability': single_result['prediction']['probabilities'].get('Cancer', 0),
                    'predicted_label': single_result['prediction']['predicted_label'],
                    'confidence': single_result['prediction']['confidence']
                }

        # Add metadata
        result['dicom_metadata'] = {
            'modality': metadata.modality,
            'series_description': metadata.series_description,
            'study_date': metadata.study_date
        }

        # Generate report if requested
        if generate_report:
            result['report'] = self._generate_report(result)

        return result

    def _generate_report(self, result: Dict[str, Any]) -> str:
        """Generate text report from prediction results."""
        report_lines = [
            "=" * 60,
            "BREAST MRI ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Analysis Date: {self._get_timestamp()}",
            "",
            "FINDINGS:",
            "-" * 40,
            f"Prediction: {result.get('predicted_label', 'N/A')}",
            f"Confidence: {result.get('confidence', 0) * 100:.1f}%",
            f"Cancer Probability: {result.get('final_probability', 0) * 100:.1f}%",
            "",
        ]

        if 'most_suspicious_slice' in result:
            report_lines.extend([
                f"Most Suspicious Slice: #{result['most_suspicious_slice'] + 1}",
                f"Total Slices Analyzed: {result.get('num_slices', 'N/A')}",
                "",
            ])

        if 'dicom_metadata' in result:
            meta = result['dicom_metadata']
            report_lines.extend([
                "SCAN INFORMATION:",
                "-" * 40,
                f"Modality: {meta.get('modality', 'N/A')}",
                f"Series: {meta.get('series_description', 'N/A')}",
                f"Study Date: {meta.get('study_date', 'N/A')}",
                "",
            ])

        report_lines.extend([
            "DISCLAIMER:",
            "-" * 40,
            "This analysis is provided for research purposes only.",
            "It should not be used as a substitute for professional",
            "medical diagnosis. Please consult a qualified healthcare",
            "provider for medical advice.",
            "",
            "=" * 60,
        ])

        return "\n".join(report_lines)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
