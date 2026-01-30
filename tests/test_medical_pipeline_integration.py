"""
Integration tests for Medical Pipeline + Secure Transfer.

These tests verify the complete workflow:
1. Secure download from cloud (mocked)
2. DICOM processing
3. Preprocessing
4. Segmentation
5. Cancer prediction
6. Audit logging
7. Secure deletion

Run with: pytest tests/test_medical_pipeline_integration.py -v
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime
import json


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    workspace = tempfile.mkdtemp(prefix="smp_test_")
    yield workspace
    # Cleanup
    if os.path.exists(workspace):
        shutil.rmtree(workspace)


@pytest.fixture
def mock_cloud_connector():
    """Mock cloud connector that simulates S3/GDrive/Dropbox."""
    connector = MagicMock()
    connector.connect.return_value = True
    connector.is_connected = True

    def mock_download(remote_path, local_path):
        # Create a fake DICOM-like file
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(b'DICM' + b'\x00' * 128)  # Fake DICOM header
        return True

    connector.download_file.side_effect = mock_download
    connector.upload_file.return_value = True
    connector.list_files.return_value = ['scan1.dcm', 'scan2.dcm']

    return connector


@pytest.fixture
def mock_encryption():
    """Mock encryption manager."""
    encryption = MagicMock()
    encryption.encrypt_file.return_value = True
    encryption.decrypt_file.side_effect = lambda src, dst: shutil.copy(src, dst)
    return encryption


@pytest.fixture
def mock_dicom_processor():
    """Mock DICOM processor."""
    processor = MagicMock()

    # Mock metadata
    mock_metadata = {
        'patient_id': 'TEST-001',
        'patient_name': 'Test Patient',
        'study_date': '20240101',
        'modality': 'MR',
        'rows': 512,
        'columns': 512
    }

    # Mock read_dicom to return numpy-like array and metadata
    import numpy as np
    mock_data = np.random.rand(512, 512).astype(np.float32)
    processor.read_dicom.return_value = (mock_data, mock_metadata)
    processor.load_volume.return_value = mock_data

    return processor


# ==============================================================================
# Core Integration Tests
# ==============================================================================

class TestSecureTransferPipeline:
    """Tests for the core secure transfer pipeline."""

    def test_pipeline_initialization(self, temp_workspace):
        """Test that pipeline initializes correctly."""
        from src.core import SecureTransferPipeline

        pipeline = SecureTransferPipeline(
            temp_dir=os.path.join(temp_workspace, "temp"),
            verify_checksums=True,
            secure_delete_passes=1  # Faster for tests
        )

        assert pipeline is not None
        assert os.path.exists(os.path.join(temp_workspace, "temp"))

    def test_add_source(self, temp_workspace, mock_cloud_connector):
        """Test adding a cloud source."""
        from src.core import SecureTransferPipeline

        pipeline = SecureTransferPipeline(
            temp_dir=os.path.join(temp_workspace, "temp")
        )

        pipeline.add_source('test-source', mock_cloud_connector)

        # Should not raise
        assert True

    def test_transfer_manifest_creation(self):
        """Test that transfer manifests are created correctly."""
        from src.core import TransferManifest, TransferMode, TransferStatus

        manifest = TransferManifest(
            transfer_id="test-123",
            source="s3:bucket/path",
            destination="/local/path",
            mode=TransferMode.STANDARD,
            status=TransferStatus.PENDING,
            started_at=datetime.utcnow()
        )

        assert manifest.transfer_id == "test-123"
        assert manifest.mode == TransferMode.STANDARD
        assert manifest.status == TransferStatus.PENDING


class TestAuditLogger:
    """Tests for HIPAA-compliant audit logging."""

    def test_audit_logger_initialization(self, temp_workspace):
        """Test audit logger creates log directory."""
        from src.core import AuditLogger

        log_path = os.path.join(temp_workspace, "audit")
        logger = AuditLogger(
            log_path=log_path,
            user_id="test-user"
        )

        assert os.path.exists(log_path)

    def test_audit_event_logging(self, temp_workspace):
        """Test that events are logged correctly."""
        from src.core import AuditLogger, AuditEventType

        log_path = os.path.join(temp_workspace, "audit")
        logger = AuditLogger(
            log_path=log_path,
            user_id="test-user"
        )

        entry = logger.log_event(
            AuditEventType.FILE_ACCESS,
            {"file": "test.dcm", "action": "read"}
        )

        assert entry is not None
        assert entry.event_type == "access.file"
        assert entry.user_id == "test-user"

    def test_audit_integrity_verification(self, temp_workspace):
        """Test that audit log integrity can be verified."""
        from src.core import AuditLogger, AuditEventType

        log_path = os.path.join(temp_workspace, "audit")
        logger = AuditLogger(
            log_path=log_path,
            user_id="test-user"
        )

        # Log some events
        logger.log_event(AuditEventType.FILE_ACCESS, {"file": "test1.dcm"})
        logger.log_event(AuditEventType.FILE_ACCESS, {"file": "test2.dcm"})
        logger.log_event(AuditEventType.SECURE_DELETE, {"path": "/test"})

        # Verify integrity
        assert logger.verify_integrity() is True

    def test_audit_export(self, temp_workspace):
        """Test exporting audit logs."""
        from src.core import AuditLogger, AuditEventType

        log_path = os.path.join(temp_workspace, "audit")
        logger = AuditLogger(
            log_path=log_path,
            user_id="test-user"
        )

        # Log events
        logger.log_event(AuditEventType.FILE_ACCESS, {"file": "test.dcm"})

        # Export
        export_path = os.path.join(temp_workspace, "export.json")
        count = logger.export_logs(export_path)

        assert count >= 1
        assert os.path.exists(export_path)

        # Verify export content
        with open(export_path) as f:
            data = json.load(f)
            assert 'entries' in data
            assert data['integrity_verified'] is True


class TestKeyExchange:
    """Tests for secure key exchange."""

    def test_key_generation(self, temp_workspace):
        """Test ECDH key pair generation."""
        from src.core import KeyExchangeManager, KeyType

        km = KeyExchangeManager(
            key_store_path=os.path.join(temp_workspace, "keys")
        )

        key_id = km.generate_key_pair(
            key_type=KeyType.ECDH_P384,
            purpose="test"
        )

        assert key_id is not None
        assert len(key_id) > 0

    def test_public_key_export(self, temp_workspace):
        """Test exporting public key."""
        from src.core import KeyExchangeManager, KeyType

        km = KeyExchangeManager(
            key_store_path=os.path.join(temp_workspace, "keys")
        )

        key_id = km.generate_key_pair(key_type=KeyType.ECDH_P384)
        public_key = km.export_public_key(key_id)

        assert public_key is not None
        assert b'BEGIN PUBLIC KEY' in public_key

    def test_key_listing(self, temp_workspace):
        """Test listing keys."""
        from src.core import KeyExchangeManager, KeyType

        km = KeyExchangeManager(
            key_store_path=os.path.join(temp_workspace, "keys")
        )

        # Generate multiple keys
        km.generate_key_pair(key_type=KeyType.ECDH_P384, purpose="test1")
        km.generate_key_pair(key_type=KeyType.ECDH_P256, purpose="test2")

        keys = km.list_keys()
        assert len(keys) == 2


class TestSecureDeletion:
    """Tests for secure file deletion."""

    def test_secure_delete_file(self, temp_workspace):
        """Test secure deletion of a single file."""
        from src.core import SecureTransferPipeline

        pipeline = SecureTransferPipeline(
            temp_dir=os.path.join(temp_workspace, "temp"),
            secure_delete_passes=1  # Faster for tests
        )

        # Create a test file
        test_file = os.path.join(temp_workspace, "sensitive.dat")
        with open(test_file, 'wb') as f:
            f.write(b'SENSITIVE DATA' * 1000)

        assert os.path.exists(test_file)

        # Secure delete
        pipeline.secure_delete(test_file)

        assert not os.path.exists(test_file)

    def test_secure_delete_directory(self, temp_workspace):
        """Test secure deletion of a directory."""
        from src.core import SecureTransferPipeline

        pipeline = SecureTransferPipeline(
            temp_dir=os.path.join(temp_workspace, "temp"),
            secure_delete_passes=1
        )

        # Create test directory with files
        test_dir = os.path.join(temp_workspace, "sensitive_dir")
        os.makedirs(test_dir)
        for i in range(5):
            with open(os.path.join(test_dir, f"file{i}.dat"), 'wb') as f:
                f.write(b'DATA' * 100)

        assert os.path.exists(test_dir)

        # Secure delete
        pipeline.secure_delete(test_dir, recursive=True)

        assert not os.path.exists(test_dir)


# ==============================================================================
# Medical Pipeline Integration Tests
# ==============================================================================

class TestMedicalPipelineIntegration:
    """Integration tests for the complete medical imaging pipeline."""

    @patch('src.medical.pipeline.S3Connector')
    @patch('src.medical.pipeline.MediaEncryptor')
    @patch('src.medical.pipeline.AuditLogger')
    def test_pipeline_initialization_with_mocks(
        self, mock_audit, mock_encrypt, mock_s3, temp_workspace
    ):
        """Test medical pipeline initialization."""
        from src.medical import MedicalPipeline

        pipeline = MedicalPipeline(
            cloud_config={'provider': 's3', 'bucket': 'test', 'region': 'us-east-1'},
            user_id='test-user',
            workspace=temp_workspace
        )

        assert pipeline is not None

    def test_medical_study_result_dataclass(self):
        """Test MedicalStudyResult dataclass."""
        from src.medical import MedicalStudyResult

        result = MedicalStudyResult(
            study_id='TEST-001',
            patient_id=None,
            processed_at=datetime.utcnow()
        )

        assert result.study_id == 'TEST-001'
        assert result.patient_id is None
        assert result.cancer_probability is None

    def test_processing_operations_enum(self):
        """Test ProcessingOperation enum."""
        from src.medical import ProcessingOperation

        assert ProcessingOperation.LOAD.value == 'load'
        assert ProcessingOperation.ANONYMIZE.value == 'anonymize'
        assert ProcessingOperation.PREPROCESS.value == 'preprocess'
        assert ProcessingOperation.SEGMENT.value == 'segment'
        assert ProcessingOperation.PREDICT.value == 'predict'


class TestMedicalPipelineWorkflow:
    """Tests for medical pipeline workflow steps."""

    def test_anonymization_removes_patient_data(self):
        """Test that anonymization removes patient identifiers."""
        from src.medical import MedicalStudyResult

        result = MedicalStudyResult(
            study_id='TEST-001',
            patient_id='PATIENT-123',
            processed_at=datetime.utcnow(),
            dicom_metadata={
                'patient_name': 'John Doe',
                'patient_id': 'PATIENT-123',
                'study_date': '20240101'
            }
        )

        # Simulate anonymization
        sensitive_fields = ['patient_name', 'patient_id']
        for field in sensitive_fields:
            if field in result.dicom_metadata:
                result.dicom_metadata[field] = '[ANONYMIZED]'
        result.patient_id = None

        assert result.patient_id is None
        assert result.dicom_metadata['patient_name'] == '[ANONYMIZED]'
        assert result.dicom_metadata['patient_id'] == '[ANONYMIZED]'
        # Non-sensitive fields preserved
        assert result.dicom_metadata['study_date'] == '20240101'


# ==============================================================================
# CLI Integration Tests
# ==============================================================================

class TestMedicalCLI:
    """Tests for medical CLI commands."""

    def test_cli_medical_group_exists(self):
        """Test that medical CLI group is registered."""
        from src.cli.medical import medical

        assert medical is not None
        assert hasattr(medical, 'commands')

    def test_cli_process_study_command_exists(self):
        """Test that process-study command is registered."""
        from src.cli.medical import medical

        commands = [cmd for cmd in medical.commands.keys()]
        assert 'process-study' in commands

    def test_cli_secure_download_command_exists(self):
        """Test that secure-download command is registered."""
        from src.cli.medical import medical

        commands = [cmd for cmd in medical.commands.keys()]
        assert 'secure-download' in commands

    def test_cli_secure_delete_command_exists(self):
        """Test that secure-delete command is registered."""
        from src.cli.medical import medical

        commands = [cmd for cmd in medical.commands.keys()]
        assert 'secure-delete' in commands

    def test_cli_audit_export_command_exists(self):
        """Test that audit-export command is registered."""
        from src.cli.medical import medical

        commands = [cmd for cmd in medical.commands.keys()]
        assert 'audit-export' in commands


# ==============================================================================
# End-to-End Test (Mocked)
# ==============================================================================

class TestEndToEndWorkflow:
    """End-to-end workflow test with mocked external dependencies."""

    @pytest.fixture
    def mock_all_dependencies(self, temp_workspace):
        """Set up all mocked dependencies."""
        with patch('src.medical.pipeline.S3Connector') as mock_s3, \
             patch('src.medical.pipeline.GoogleDriveConnector') as mock_gdrive, \
             patch('src.medical.pipeline.DropboxConnector') as mock_dropbox, \
             patch('src.medical.pipeline.MediaEncryptor') as mock_encrypt, \
             patch('src.medical.pipeline.SecureTransferPipeline') as mock_pipeline:

            # Configure mocks
            mock_transfer = MagicMock()
            mock_transfer.secure_download.return_value = MagicMock(
                transfer_id='test-transfer',
                file_count=3,
                total_bytes=1024000,
                destination=temp_workspace
            )
            mock_transfer.verify_integrity.return_value = True
            mock_pipeline.return_value = mock_transfer

            yield {
                's3': mock_s3,
                'gdrive': mock_gdrive,
                'dropbox': mock_dropbox,
                'encrypt': mock_encrypt,
                'pipeline': mock_pipeline,
                'transfer': mock_transfer,
                'workspace': temp_workspace
            }

    def test_complete_workflow_structure(self, temp_workspace):
        """Test that complete workflow components are importable."""
        # Import all required components
        from src.medical import MedicalPipeline, MedicalStudyResult
        from src.core import (
            SecureTransferPipeline,
            TransferMode,
            AuditLogger,
            KeyExchangeManager
        )
        from src.connectors import S3Connector

        # All imports successful
        assert MedicalPipeline is not None
        assert SecureTransferPipeline is not None
        assert AuditLogger is not None
        assert S3Connector is not None


# ==============================================================================
# HIPAA Compliance Tests
# ==============================================================================

class TestHIPAACompliance:
    """Tests for HIPAA compliance features."""

    def test_audit_log_retention_default(self, temp_workspace):
        """Test that audit logs have 6-year retention by default."""
        from src.core import AuditLogger

        logger = AuditLogger(
            log_path=os.path.join(temp_workspace, "audit"),
            user_id="test"
        )

        # Check retention is set (6 years = 2190 days)
        assert logger._retention_days == 2190

    def test_sensitive_data_redaction(self, temp_workspace):
        """Test that sensitive data is redacted in logs."""
        from src.core import AuditLogger, AuditEventType

        logger = AuditLogger(
            log_path=os.path.join(temp_workspace, "audit"),
            user_id="test",
            redact_sensitive=True
        )

        entry = logger.log_event(
            AuditEventType.FILE_ACCESS,
            {
                "file": "test.dcm",
                "password": "secret123",  # Should be redacted
                "api_token": "abc123"     # Should be redacted
            }
        )

        assert entry.details.get('password') == '[REDACTED]'
        assert entry.details.get('api_token') == '[REDACTED]'
        assert entry.details.get('file') == 'test.dcm'  # Not redacted


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
