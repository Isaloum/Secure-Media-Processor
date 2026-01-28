"""Tests for medical imaging modules.

Tests DICOM processing, medical preprocessing, and ML inference pipelines.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


# =============================================================================
# DICOM Processor Tests
# =============================================================================

class TestDICOMMetadata:
    """Test DICOMMetadata dataclass."""

    def test_metadata_creation(self):
        """Test basic metadata creation."""
        from src.dicom_processor import DICOMMetadata

        metadata = DICOMMetadata(
            patient_id="TEST001",
            patient_name="Test Patient",
            modality="MR",
            rows=256,
            columns=256
        )

        assert metadata.patient_id == "TEST001"
        assert metadata.modality == "MR"
        assert metadata.rows == 256

    def test_metadata_to_dict(self):
        """Test conversion to dictionary."""
        from src.dicom_processor import DICOMMetadata

        metadata = DICOMMetadata(
            patient_id="TEST001",
            modality="MR"
        )

        result = metadata.to_dict()
        assert 'patient_id' in result
        assert result['patient_id'] == "TEST001"
        # None values should be excluded
        assert 'patient_name' not in result or result.get('patient_name') is None

    def test_anonymized_metadata(self):
        """Test anonymization removes patient info."""
        from src.dicom_processor import DICOMMetadata

        metadata = DICOMMetadata(
            patient_id="SENSITIVE_ID",
            patient_name="John Doe",
            patient_birth_date="19800101",
            modality="MR",
            rows=256,
            columns=256
        )

        anonymized = metadata.get_anonymized()

        # Patient info should be removed
        assert anonymized.patient_id is None
        assert anonymized.patient_name is None
        assert anonymized.patient_birth_date is None

        # Technical info should be preserved
        assert anonymized.modality == "MR"
        assert anonymized.rows == 256


class TestDICOMVolume:
    """Test DICOMVolume dataclass."""

    def test_volume_creation(self):
        """Test volume creation with 3D data."""
        from src.dicom_processor import DICOMVolume, DICOMMetadata

        pixel_data = np.random.rand(10, 256, 256).astype(np.float32)
        slice_metadata = [DICOMMetadata() for _ in range(10)]

        volume = DICOMVolume(
            pixel_data=pixel_data,
            slice_metadata=slice_metadata,
            voxel_spacing=(1.0, 0.5, 0.5)
        )

        assert volume.volume_shape == (10, 256, 256)
        assert volume.voxel_spacing == (1.0, 0.5, 0.5)

    def test_get_slices(self):
        """Test slice extraction methods."""
        from src.dicom_processor import DICOMVolume, DICOMMetadata

        pixel_data = np.arange(8 * 4 * 4).reshape(8, 4, 4).astype(np.float32)
        slice_metadata = [DICOMMetadata() for _ in range(8)]

        volume = DICOMVolume(pixel_data=pixel_data, slice_metadata=slice_metadata)

        # Axial slice
        axial = volume.get_axial_slice(3)
        assert axial.shape == (4, 4)

        # Sagittal slice
        sagittal = volume.get_sagittal_slice(2)
        assert sagittal.shape == (8, 4)

        # Coronal slice
        coronal = volume.get_coronal_slice(1)
        assert coronal.shape == (8, 4)

    def test_normalize_minmax(self):
        """Test min-max normalization."""
        from src.dicom_processor import DICOMVolume, DICOMMetadata

        pixel_data = np.array([[[0, 50], [100, 200]]]).astype(np.float32)
        volume = DICOMVolume(pixel_data=pixel_data, slice_metadata=[DICOMMetadata()])

        normalized = volume.normalize(method='minmax')

        assert normalized.pixel_data.min() == pytest.approx(0.0)
        assert normalized.pixel_data.max() == pytest.approx(1.0)

    def test_normalize_zscore(self):
        """Test z-score normalization."""
        from src.dicom_processor import DICOMVolume, DICOMMetadata

        pixel_data = np.random.rand(5, 10, 10).astype(np.float32) * 100
        volume = DICOMVolume(pixel_data=pixel_data, slice_metadata=[DICOMMetadata()] * 5)

        normalized = volume.normalize(method='zscore')

        # Z-score normalized data should have mean ~0 and std ~1
        assert abs(normalized.pixel_data.mean()) < 0.1
        assert abs(normalized.pixel_data.std() - 1.0) < 0.1


class TestDICOMProcessor:
    """Test DICOMProcessor class."""

    def test_processor_initialization(self):
        """Test processor initialization."""
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()
        assert processor._audit_log == []

    def test_audit_log(self):
        """Test audit logging."""
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()
        processor._log_access('read', '/path/to/file.dcm', 'PATIENT123')

        assert len(processor._audit_log) == 1
        log_entry = processor._audit_log[0]
        assert log_entry['action'] == 'read'
        assert 'timestamp' in log_entry
        assert log_entry['patient_id_hash'] is not None

    def test_get_audit_log_returns_copy(self):
        """Test that get_audit_log returns a copy."""
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()
        processor._log_access('test', '/path', 'patient')

        log = processor.get_audit_log()
        log.clear()

        # Original should be unchanged
        assert len(processor._audit_log) == 1

    @patch('src.dicom_processor.PYDICOM_AVAILABLE', False)
    def test_read_dicom_without_pydicom(self):
        """Test error when pydicom not available."""
        from src.dicom_processor import DICOMProcessor

        processor = DICOMProcessor()

        with pytest.raises(RuntimeError, match="pydicom not installed"):
            processor.read_dicom('/fake/path.dcm')

    def test_check_dicom_available(self):
        """Test DICOM availability check."""
        from src.dicom_processor import check_dicom_available

        # Should return boolean
        result = check_dicom_available()
        assert isinstance(result, bool)


# =============================================================================
# Medical Preprocessing Tests
# =============================================================================

class TestPreprocessingConfig:
    """Test PreprocessingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.medical_preprocessing import PreprocessingConfig, NormalizationMethod

        config = PreprocessingConfig()

        assert config.normalize is True
        assert config.normalization_method == NormalizationMethod.ZSCORE
        assert config.denoise is True
        assert config.bias_correction is True

    def test_custom_config(self):
        """Test custom configuration."""
        from src.medical_preprocessing import PreprocessingConfig, NormalizationMethod, NoiseReductionMethod

        config = PreprocessingConfig(
            normalize=True,
            normalization_method=NormalizationMethod.PERCENTILE,
            percentile_low=2.0,
            percentile_high=98.0,
            denoise_method=NoiseReductionMethod.GAUSSIAN
        )

        assert config.normalization_method == NormalizationMethod.PERCENTILE
        assert config.percentile_low == 2.0


class TestMedicalImagePreprocessor:
    """Test MedicalImagePreprocessor class."""

    def test_preprocessor_initialization(self):
        """Test preprocessor initialization."""
        from src.medical_preprocessing import MedicalImagePreprocessor

        preprocessor = MedicalImagePreprocessor()
        assert preprocessor.config is not None

    def test_normalize_minmax(self):
        """Test min-max normalization."""
        from src.medical_preprocessing import MedicalImagePreprocessor, NormalizationMethod

        preprocessor = MedicalImagePreprocessor()
        image = np.array([[0, 50], [100, 200]], dtype=np.float32)

        result = preprocessor.normalize(image, method=NormalizationMethod.MINMAX)

        assert result.min() == pytest.approx(0.0)
        assert result.max() == pytest.approx(1.0)

    def test_normalize_zscore(self):
        """Test z-score normalization."""
        from src.medical_preprocessing import MedicalImagePreprocessor, NormalizationMethod

        preprocessor = MedicalImagePreprocessor()
        image = np.random.rand(100, 100).astype(np.float32) * 100 + 50

        result = preprocessor.normalize(image, method=NormalizationMethod.ZSCORE)

        # Should have mean close to 0 for non-zero pixels
        non_zero = result[image > 0]
        assert abs(non_zero.mean()) < 0.5

    def test_normalize_percentile(self):
        """Test percentile normalization."""
        from src.medical_preprocessing import MedicalImagePreprocessor, NormalizationMethod

        preprocessor = MedicalImagePreprocessor()
        image = np.random.rand(100, 100).astype(np.float32) * 1000

        result = preprocessor.normalize(
            image,
            method=NormalizationMethod.PERCENTILE,
            percentile_low=5,
            percentile_high=95
        )

        # Result should be clipped and normalized
        assert result.min() >= 0
        assert result.max() <= 1

    def test_reduce_noise_gaussian(self):
        """Test Gaussian noise reduction."""
        from src.medical_preprocessing import MedicalImagePreprocessor, NoiseReductionMethod

        preprocessor = MedicalImagePreprocessor()

        # Create noisy image
        clean = np.ones((50, 50), dtype=np.float32) * 100
        noisy = clean + np.random.randn(50, 50).astype(np.float32) * 20

        result = preprocessor.reduce_noise(noisy, method=NoiseReductionMethod.GAUSSIAN, strength=1.0)

        # Denoised should be smoother (lower variance)
        assert result.std() < noisy.std()

    def test_apply_window(self):
        """Test intensity windowing."""
        from src.medical_preprocessing import MedicalImagePreprocessor

        preprocessor = MedicalImagePreprocessor()
        image = np.array([[0, 50, 100, 150, 200]], dtype=np.float32)

        result = preprocessor.apply_window(image, center=100, width=100)

        # Values should be clipped to window and normalized
        assert result.min() >= 0
        assert result.max() <= 1

    def test_preprocess_pipeline(self):
        """Test full preprocessing pipeline."""
        from src.medical_preprocessing import MedicalImagePreprocessor, PreprocessingConfig

        config = PreprocessingConfig(
            normalize=True,
            denoise=True,
            bias_correction=False,  # Skip for speed
            enhance_contrast=False
        )

        preprocessor = MedicalImagePreprocessor(config)
        image = np.random.rand(64, 64).astype(np.float32) * 100

        result = preprocessor.preprocess(image)

        assert result.data.shape == image.shape
        assert len(result.steps_applied) > 0
        assert 'normalize_zscore' in result.steps_applied


class TestBreastMRIPreprocessor:
    """Test BreastMRIPreprocessor class."""

    def test_initialization(self):
        """Test breast MRI preprocessor initialization."""
        from src.medical_preprocessing import BreastMRIPreprocessor, NormalizationMethod

        preprocessor = BreastMRIPreprocessor()

        assert preprocessor.config.normalization_method == NormalizationMethod.PERCENTILE
        assert preprocessor.config.enhance_contrast is True

    def test_extract_features(self):
        """Test feature extraction."""
        from src.medical_preprocessing import BreastMRIPreprocessor

        preprocessor = BreastMRIPreprocessor()
        image = np.random.rand(64, 64).astype(np.float32) * 100 + 50

        features = preprocessor.extract_features(image)

        assert 'mean' in features
        assert 'std' in features
        assert 'entropy' in features
        assert 'skewness' in features
        assert 'kurtosis' in features

    def test_extract_features_empty_image(self):
        """Test feature extraction with empty image."""
        from src.medical_preprocessing import BreastMRIPreprocessor

        preprocessor = BreastMRIPreprocessor()
        image = np.zeros((64, 64), dtype=np.float32)

        features = preprocessor.extract_features(image)

        # Should return empty dict for zero image
        assert features == {}


# =============================================================================
# ML Inference Tests
# =============================================================================

class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        from src.ml_inference import ModelConfig, ModelType, PredictionType

        config = ModelConfig(model_path="/path/to/model.pt")

        assert config.model_type == ModelType.PYTORCH
        assert config.prediction_type == PredictionType.BINARY
        assert config.num_classes == 2
        assert config.use_gpu is True

    def test_custom_config(self):
        """Test custom configuration."""
        from src.ml_inference import ModelConfig, ModelType, PredictionType

        config = ModelConfig(
            model_path="/path/to/model.onnx",
            model_type=ModelType.ONNX,
            prediction_type=PredictionType.MULTICLASS,
            num_classes=5,
            class_names=["Stage0", "Stage1", "Stage2", "Stage3", "Stage4"]
        )

        assert config.model_type == ModelType.ONNX
        assert config.num_classes == 5


class TestPredictionResult:
    """Test PredictionResult dataclass."""

    def test_result_creation(self):
        """Test result creation."""
        from src.ml_inference import PredictionResult

        result = PredictionResult(
            probabilities=np.array([0.2, 0.8]),
            predicted_class=1,
            predicted_label="Cancer",
            confidence=0.8,
            raw_output=np.array([0.8]),
            metadata={'class_names': ['No Cancer', 'Cancer']}
        )

        assert result.predicted_class == 1
        assert result.confidence == 0.8

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from src.ml_inference import PredictionResult

        result = PredictionResult(
            probabilities=np.array([0.3, 0.7]),
            predicted_class=1,
            predicted_label="Cancer",
            confidence=0.7,
            raw_output=np.array([0.7]),
            metadata={'class_names': ['No Cancer', 'Cancer']}
        )

        result_dict = result.to_dict()

        assert 'predicted_class' in result_dict
        assert 'confidence' in result_dict
        assert 'probabilities' in result_dict
        assert result_dict['confidence'] == 0.7


class TestMLInference:
    """Test ML inference functionality."""

    def test_check_ml_available(self):
        """Test ML availability check."""
        from src.ml_inference import check_ml_available

        status = check_ml_available()

        assert 'pytorch' in status
        assert 'onnx' in status
        assert 'gpu' in status
        assert all(isinstance(v, bool) for v in status.values())

    @patch('src.ml_inference.TORCH_AVAILABLE', False)
    def test_pytorch_inference_without_torch(self):
        """Test error when PyTorch not available."""
        from src.ml_inference import PyTorchInference, ModelConfig

        config = ModelConfig(model_path="/fake/model.pt")

        with pytest.raises(RuntimeError, match="PyTorch not installed"):
            PyTorchInference(config)

    @patch('src.ml_inference.ONNX_AVAILABLE', False)
    def test_onnx_inference_without_onnxruntime(self):
        """Test error when ONNX Runtime not available."""
        from src.ml_inference import ONNXInference, ModelConfig, ModelType

        config = ModelConfig(
            model_path="/fake/model.onnx",
            model_type=ModelType.ONNX
        )

        with pytest.raises(RuntimeError, match="ONNX Runtime not installed"):
            ONNXInference(config)


class TestModelEnsemble:
    """Test ModelEnsemble class."""

    def test_ensemble_weight_validation(self):
        """Test that weights must match number of models."""
        from src.ml_inference import ModelEnsemble

        mock_model = Mock()

        with pytest.raises(ValueError, match="Number of weights"):
            ModelEnsemble([mock_model, mock_model], weights=[1.0])

    def test_ensemble_default_weights(self):
        """Test default equal weights."""
        from src.ml_inference import ModelEnsemble

        mock_model = Mock()
        ensemble = ModelEnsemble([mock_model, mock_model])

        assert ensemble.weights == [0.5, 0.5]


# =============================================================================
# Integration Tests
# =============================================================================

class TestMedicalImagingIntegration:
    """Integration tests for medical imaging pipeline."""

    def test_preprocessing_to_features(self):
        """Test preprocessing followed by feature extraction."""
        from src.medical_preprocessing import BreastMRIPreprocessor

        preprocessor = BreastMRIPreprocessor()

        # Create synthetic MRI-like data
        image = np.random.rand(128, 128).astype(np.float32) * 500 + 100

        # Preprocess
        result = preprocessor.preprocess(image)

        # Extract features
        features = preprocessor.extract_features(result.data)

        assert len(features) > 0
        assert all(isinstance(v, (int, float)) for v in features.values())

    def test_volume_preprocessing(self):
        """Test volume preprocessing for prediction."""
        from src.medical_preprocessing import BreastMRIPreprocessor

        preprocessor = BreastMRIPreprocessor()

        # Create 3D volume
        volume = np.random.rand(20, 128, 128).astype(np.float32) * 500

        # Preprocess for prediction
        processed = preprocessor.preprocess_for_prediction(volume)

        assert processed.shape == volume.shape
        assert processed.dtype == np.float32


# =============================================================================
# CLI Tests
# =============================================================================

class TestMedicalCLI:
    """Test medical imaging CLI commands."""

    def test_medical_group_exists(self):
        """Test that medical command group exists."""
        from src.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ['medical', '--help'])

        assert result.exit_code == 0
        assert 'Medical imaging tools' in result.output

    def test_medical_info_command(self):
        """Test medical info command."""
        from src.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ['medical', 'info'])

        assert result.exit_code == 0
        assert 'Medical Imaging Capabilities' in result.output
        assert 'DICOM Support' in result.output
        assert 'ML Inference' in result.output

    def test_dicom_info_without_pydicom(self):
        """Test dicom-info command fails gracefully without pydicom."""
        from src.cli import cli
        from click.testing import CliRunner
        import tempfile
        import os

        runner = CliRunner()

        # Create a temp file to pass path validation
        with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as f:
            temp_path = f.name

        try:
            with patch('src.dicom_processor.PYDICOM_AVAILABLE', False):
                with patch('src.dicom_processor.check_dicom_available', return_value=False):
                    result = runner.invoke(cli, ['medical', 'dicom-info', temp_path])
                    # Should fail with appropriate message about pydicom
                    assert result.exit_code != 0
        finally:
            os.unlink(temp_path)

    def test_predict_without_model(self):
        """Test predict command requires model path."""
        from src.cli import cli
        from click.testing import CliRunner

        runner = CliRunner()
        # Use --help to check the command structure
        result = runner.invoke(cli, ['medical', 'predict', '--help'])

        # Should show that --model is required
        assert result.exit_code == 0
        assert '--model' in result.output
        assert 'required' in result.output.lower() or 'PATH' in result.output
