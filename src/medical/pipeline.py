"""
Medical Imaging Pipeline

A complete, secure pipeline for medical imaging workflows:
1. Securely download medical images from cloud (HIPAA compliant)
2. Process with GPU-accelerated algorithms
3. Run cancer prediction / segmentation models
4. Secure cleanup after processing

This module integrates:
- Secure Transfer Pipeline (encryption, audit logging)
- DICOM Processing
- MRI Preprocessing
- U-Net Segmentation
- Cancer Prediction Inference

Example:
    from src.medical.pipeline import MedicalPipeline

    # Initialize pipeline
    pipeline = MedicalPipeline(
        cloud_config={'provider': 's3', 'bucket': 'hospital-data'},
        audit_config={'user_id': 'researcher@hospital.org'}
    )

    # Complete workflow
    results = pipeline.process_study(
        remote_path='mri-scans/patient-001/',
        operations=['preprocess', 'segment', 'predict']
    )

    # Results contain predictions, segmentation masks, etc.
    print(results.cancer_probability)

    # Automatic secure cleanup
    pipeline.cleanup()
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingOperation(Enum):
    """Available processing operations."""
    LOAD = "load"
    ANONYMIZE = "anonymize"
    PREPROCESS = "preprocess"
    SEGMENT = "segment"
    PREDICT = "predict"


@dataclass
class MedicalStudyResult:
    """Results from processing a medical imaging study."""
    study_id: str
    patient_id: Optional[str]  # None if anonymized
    processed_at: datetime

    # Data
    dicom_metadata: Optional[Dict[str, Any]] = None
    preprocessed_volume: Optional[Any] = None  # numpy array
    segmentation_mask: Optional[Any] = None  # numpy array

    # Predictions
    cancer_probability: Optional[float] = None
    cancer_prediction: Optional[str] = None  # "positive", "negative", "uncertain"
    confidence_score: Optional[float] = None

    # Audit
    operations_performed: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    audit_log_path: Optional[str] = None

    # Paths (for secure deletion later)
    local_paths: List[str] = field(default_factory=list)


class MedicalPipeline:
    """
    Secure medical imaging pipeline.

    Combines secure data transfer with medical image processing
    for HIPAA-compliant workflows.

    Features:
    - End-to-end encryption for data transfer
    - HIPAA/GDPR compliant audit logging
    - GPU-accelerated processing
    - Automatic anonymization option
    - Secure deletion after processing

    Example:
        # Initialize
        pipeline = MedicalPipeline(
            cloud_config={
                'provider': 's3',
                'bucket': 'hospital-encrypted-data',
                'region': 'us-east-1'
            },
            encryption_key_path='~/.smp/keys/master.key',
            audit_log_path='~/.smp/audit/',
            user_id='researcher@university.edu',
            workspace='/secure/medical-workspace/'
        )

        # Process a study
        results = pipeline.process_study(
            remote_path='studies/BREAST-MRI-001/',
            operations=['anonymize', 'preprocess', 'segment', 'predict']
        )

        # Check results
        if results.cancer_probability > 0.7:
            print("High risk detected")

        # Cleanup (secure deletion)
        pipeline.cleanup()
    """

    def __init__(
        self,
        cloud_config: Optional[Dict[str, Any]] = None,
        encryption_key_path: str = "~/.smp/keys/master.key",
        audit_log_path: str = "~/.smp/audit/",
        user_id: str = "anonymous",
        workspace: str = "~/.smp/medical-workspace/",
        model_path: Optional[str] = None,
        device: str = "auto",
        auto_anonymize: bool = True,
        auto_cleanup: bool = False
    ):
        """
        Initialize the medical imaging pipeline.

        Args:
            cloud_config: Cloud storage configuration
                - provider: 's3', 'google_drive', or 'dropbox'
                - bucket/folder: Storage location
                - Additional provider-specific options
            encryption_key_path: Path to encryption key
            audit_log_path: Path for audit logs
            user_id: User identifier for audit trail
            workspace: Local workspace for processing
            model_path: Path to ML model weights
            device: 'auto', 'cuda', 'mps', or 'cpu'
            auto_anonymize: Automatically anonymize DICOM data
            auto_cleanup: Automatically cleanup after processing
        """
        self._cloud_config = cloud_config or {}
        self._encryption_key_path = Path(encryption_key_path).expanduser()
        self._audit_log_path = Path(audit_log_path).expanduser()
        self._user_id = user_id
        self._workspace = Path(workspace).expanduser()
        self._model_path = model_path
        self._device = device
        self._auto_anonymize = auto_anonymize
        self._auto_cleanup = auto_cleanup

        # Components (lazy loaded)
        self._transfer_pipeline = None
        self._dicom_processor = None
        self._preprocessor = None
        self._segmentation = None
        self._inference = None
        self._audit_logger = None

        # State
        self._active_results: List[MedicalStudyResult] = []

        # Create workspace
        self._workspace.mkdir(parents=True, exist_ok=True)
        os.chmod(self._workspace, 0o700)

    def _init_transfer_pipeline(self):
        """Initialize the secure transfer pipeline."""
        if self._transfer_pipeline is not None:
            return

        from src.core import (
            SecureTransferPipeline,
            MediaEncryptor,
            AuditLogger
        )
        from src.connectors import S3Connector, GoogleDriveConnector, DropboxConnector

        # Initialize encryption
        encryption = MediaEncryptor(str(self._encryption_key_path))

        # Initialize audit logger
        self._audit_logger = AuditLogger(
            log_path=str(self._audit_log_path),
            user_id=self._user_id,
            retention_days=2190,  # 6 years for HIPAA
            redact_sensitive=True
        )

        # Create pipeline
        self._transfer_pipeline = SecureTransferPipeline(
            encryption=encryption,
            audit_logger=self._audit_logger,
            temp_dir=str(self._workspace / "temp"),
            verify_checksums=True,
            secure_delete_passes=3
        )

        # Add cloud connector based on config
        provider = self._cloud_config.get('provider', 's3')

        if provider == 's3':
            connector = S3Connector(
                bucket_name=self._cloud_config.get('bucket', ''),
                region=self._cloud_config.get('region', 'us-east-1')
            )
        elif provider == 'google_drive':
            connector = GoogleDriveConnector(
                credentials_path=self._cloud_config.get('credentials_path'),
                folder_id=self._cloud_config.get('folder_id')
            )
        elif provider == 'dropbox':
            connector = DropboxConnector(
                access_token=self._cloud_config.get('access_token')
            )
        else:
            raise ValueError(f"Unknown cloud provider: {provider}")

        self._transfer_pipeline.add_source('medical-data', connector)
        logger.info(f"Initialized transfer pipeline with {provider} connector")

    def _init_dicom_processor(self):
        """Initialize DICOM processor."""
        if self._dicom_processor is not None:
            return

        from src.medical import DICOMProcessor
        self._dicom_processor = DICOMProcessor()
        logger.info("Initialized DICOM processor")

    def _init_preprocessor(self):
        """Initialize MRI preprocessor."""
        if self._preprocessor is not None:
            return

        from src.medical import BreastMRIPreprocessor
        self._preprocessor = BreastMRIPreprocessor()
        logger.info("Initialized MRI preprocessor")

    def _init_segmentation(self):
        """Initialize U-Net segmentation."""
        if self._segmentation is not None:
            return

        from src.medical import UNetSegmentation, SegmentationConfig, check_segmentation_available

        if not check_segmentation_available():
            logger.warning("PyTorch not available - segmentation disabled")
            return

        config = SegmentationConfig(
            device=self._device,
            model_path=self._model_path
        )
        self._segmentation = UNetSegmentation(config)
        logger.info("Initialized U-Net segmentation")

    def _init_inference(self):
        """Initialize cancer prediction inference."""
        if self._inference is not None:
            return

        try:
            from src.medical.inference import CancerPredictionPipeline
            self._inference = CancerPredictionPipeline(
                model_path=self._model_path,
                device=self._device
            )
            logger.info("Initialized cancer prediction pipeline")
        except ImportError:
            logger.warning("Inference pipeline not available")

    def process_study(
        self,
        remote_path: str,
        operations: List[str] = None,
        study_id: Optional[str] = None,
        download_mode: str = "zero_knowledge",
        output_path: Optional[str] = None
    ) -> MedicalStudyResult:
        """
        Process a medical imaging study.

        This is the main entry point for medical imaging workflows.

        Args:
            remote_path: Path to study in cloud storage
            operations: List of operations to perform:
                - 'load': Load DICOM files
                - 'anonymize': Remove patient identifiers
                - 'preprocess': MRI preprocessing
                - 'segment': U-Net segmentation
                - 'predict': Cancer prediction
            study_id: Optional study identifier
            download_mode: 'standard' or 'zero_knowledge'
            output_path: Where to save results (optional)

        Returns:
            MedicalStudyResult with all processing results
        """
        if operations is None:
            operations = ['load', 'preprocess', 'segment', 'predict']

        start_time = datetime.utcnow()

        # Generate study ID if not provided
        if study_id is None:
            import uuid
            study_id = f"study-{uuid.uuid4().hex[:8]}"

        # Create result object
        result = MedicalStudyResult(
            study_id=study_id,
            patient_id=None,
            processed_at=start_time,
            audit_log_path=str(self._audit_log_path)
        )

        try:
            # Step 1: Secure download
            local_path = self._secure_download(remote_path, study_id, download_mode)
            result.local_paths.append(str(local_path))
            result.operations_performed.append('download')

            # Step 2: Load DICOM
            if 'load' in operations:
                self._init_dicom_processor()
                dicom_data, metadata = self._load_dicom(local_path)
                result.dicom_metadata = metadata
                result.patient_id = metadata.get('patient_id')
                result.operations_performed.append('load')

            # Step 3: Anonymize (if enabled)
            if 'anonymize' in operations or self._auto_anonymize:
                if result.dicom_metadata:
                    self._anonymize(result)
                    result.patient_id = None  # Cleared
                    result.operations_performed.append('anonymize')

            # Step 4: Preprocess
            if 'preprocess' in operations:
                self._init_preprocessor()
                result.preprocessed_volume = self._preprocess(dicom_data)
                result.operations_performed.append('preprocess')

            # Step 5: Segment
            if 'segment' in operations:
                self._init_segmentation()
                if self._segmentation:
                    input_data = result.preprocessed_volume if result.preprocessed_volume is not None else dicom_data
                    result.segmentation_mask = self._segment(input_data)
                    result.operations_performed.append('segment')

            # Step 6: Predict
            if 'predict' in operations:
                self._init_inference()
                if self._inference:
                    prediction = self._predict(
                        result.preprocessed_volume,
                        result.segmentation_mask
                    )
                    result.cancer_probability = prediction.get('probability')
                    result.cancer_prediction = prediction.get('prediction')
                    result.confidence_score = prediction.get('confidence')
                    result.operations_performed.append('predict')

            # Save results if output path provided
            if output_path:
                self._save_results(result, output_path)

            # Calculate processing time
            end_time = datetime.utcnow()
            result.processing_time_seconds = (end_time - start_time).total_seconds()

            # Track for cleanup
            self._active_results.append(result)

            logger.info(f"Completed processing study {study_id} in {result.processing_time_seconds:.2f}s")

            # Auto cleanup if enabled
            if self._auto_cleanup:
                self._cleanup_result(result)

            return result

        except Exception as e:
            logger.error(f"Failed to process study {study_id}: {e}")
            # Log failure to audit
            if self._audit_logger:
                self._audit_logger.log_event(
                    self._audit_logger.AuditEventType.TRANSFER_FAILED if hasattr(self._audit_logger, 'AuditEventType') else None,
                    {"study_id": study_id, "error": str(e)}
                )
            raise

    def _secure_download(self, remote_path: str, study_id: str, mode: str) -> Path:
        """Securely download study from cloud."""
        self._init_transfer_pipeline()

        from src.core import TransferMode

        transfer_mode = TransferMode.ZERO_KNOWLEDGE if mode == "zero_knowledge" else TransferMode.STANDARD

        local_path = self._workspace / "downloads" / study_id
        local_path.mkdir(parents=True, exist_ok=True)

        manifest = self._transfer_pipeline.secure_download(
            source_name='medical-data',
            remote_path=remote_path,
            local_path=str(local_path),
            mode=transfer_mode,
            metadata={
                'study_id': study_id,
                'purpose': 'medical-imaging-analysis'
            }
        )

        # Verify integrity
        if not self._transfer_pipeline.verify_integrity(manifest):
            raise ValueError("Data integrity verification failed")

        logger.info(f"Downloaded {manifest.file_count} files for study {study_id}")
        return local_path

    def _load_dicom(self, path: Path) -> tuple:
        """Load DICOM files from path."""
        # Find all DICOM files
        dicom_files = list(path.glob("**/*.dcm")) + list(path.glob("**/*.DCM"))

        if not dicom_files:
            raise ValueError(f"No DICOM files found in {path}")

        # Load first file to get metadata (for series)
        data, metadata = self._dicom_processor.read_dicom(str(dicom_files[0]))

        # If multiple files, load as volume
        if len(dicom_files) > 1:
            volume_data = self._dicom_processor.load_volume(str(path))
            return volume_data, metadata

        return data, metadata

    def _anonymize(self, result: MedicalStudyResult):
        """Anonymize patient data in metadata."""
        sensitive_fields = [
            'patient_name', 'patient_id', 'patient_birth_date',
            'referring_physician', 'institution_name', 'station_name'
        ]

        if result.dicom_metadata:
            for field in sensitive_fields:
                if field in result.dicom_metadata:
                    result.dicom_metadata[field] = "[ANONYMIZED]"

        logger.info("Anonymized patient identifiers")

    def _preprocess(self, data):
        """Preprocess MRI data."""
        result = self._preprocessor.preprocess(data)
        return result.volume if hasattr(result, 'volume') else result

    def _segment(self, data):
        """Run U-Net segmentation."""
        result = self._segmentation.segment(data)
        return result.mask if hasattr(result, 'mask') else result

    def _predict(self, volume, mask) -> Dict[str, Any]:
        """Run cancer prediction."""
        result = self._inference.predict(volume, mask)

        # Standardize output
        if hasattr(result, 'probability'):
            return {
                'probability': result.probability,
                'prediction': 'positive' if result.probability > 0.5 else 'negative',
                'confidence': abs(result.probability - 0.5) * 2
            }

        return result if isinstance(result, dict) else {'probability': None}

    def _save_results(self, result: MedicalStudyResult, output_path: str):
        """Save processing results."""
        import json

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata and predictions as JSON
        summary = {
            'study_id': result.study_id,
            'processed_at': result.processed_at.isoformat(),
            'operations': result.operations_performed,
            'processing_time_seconds': result.processing_time_seconds,
            'cancer_probability': result.cancer_probability,
            'cancer_prediction': result.cancer_prediction,
            'confidence_score': result.confidence_score
        }

        with open(output_dir / f"{result.study_id}_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        # Save arrays if numpy available
        try:
            import numpy as np

            if result.preprocessed_volume is not None:
                np.save(output_dir / f"{result.study_id}_preprocessed.npy", result.preprocessed_volume)

            if result.segmentation_mask is not None:
                np.save(output_dir / f"{result.study_id}_segmentation.npy", result.segmentation_mask)
        except ImportError:
            pass

        logger.info(f"Saved results to {output_dir}")

    def _cleanup_result(self, result: MedicalStudyResult):
        """Securely delete data for a single result."""
        for path in result.local_paths:
            if Path(path).exists():
                self._transfer_pipeline.secure_delete(path)
                logger.info(f"Securely deleted: {path}")

    def cleanup(self):
        """Securely delete all downloaded/processed data."""
        for result in self._active_results:
            self._cleanup_result(result)

        self._active_results.clear()

        # Clean workspace temp directory
        temp_dir = self._workspace / "temp"
        if temp_dir.exists():
            self._transfer_pipeline.secure_delete(str(temp_dir))

        logger.info("Cleanup complete - all sensitive data securely deleted")

    def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit log summary for compliance reporting."""
        if self._audit_logger is None:
            return {"error": "Audit logger not initialized"}

        return {
            "total_entries": self._audit_logger.get_entry_count(),
            "log_path": str(self._audit_log_path),
            "integrity_verified": self._audit_logger.verify_integrity(),
            "user_id": self._user_id
        }

    def export_audit_log(self, output_path: str, start_date: str = None, end_date: str = None) -> int:
        """Export audit log for compliance review."""
        if self._audit_logger is None:
            self._init_transfer_pipeline()

        return self._audit_logger.export_logs(
            output_path=output_path,
            start_date=start_date,
            end_date=end_date
        )


# Convenience function
def create_medical_pipeline(**kwargs) -> MedicalPipeline:
    """Create a configured MedicalPipeline instance."""
    return MedicalPipeline(**kwargs)
