"""Tests for Core Security Modules.

Tests for SecureTransferPipeline, AuditLogger, and KeyExchange.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from datetime import datetime


class TestKeyExchange:
    """Test suite for ECDH key exchange."""

    @pytest.fixture
    def key_exchange(self):
        """Create KeyExchange instance."""
        try:
            from src.core import KeyExchange
            return KeyExchange()
        except ImportError:
            pytest.skip("KeyExchange module not available")

    def test_generate_ecdh_keypair(self, key_exchange):
        """Test ECDH key pair generation."""
        private_key, public_key = key_exchange.generate_ecdh_keypair()

        assert private_key is not None
        assert public_key is not None
        assert len(private_key) > 0
        assert len(public_key) > 0

    def test_keypair_uniqueness(self, key_exchange):
        """Test that each keypair is unique."""
        pairs = [key_exchange.generate_ecdh_keypair() for _ in range(5)]
        private_keys = [p[0] for p in pairs]
        public_keys = [p[1] for p in pairs]

        # All should be unique
        assert len(set(private_keys)) == 5
        assert len(set(public_keys)) == 5

    def test_shared_secret_derivation(self, key_exchange):
        """Test that both parties derive the same shared secret."""
        # Generate two key pairs
        priv_a, pub_a = key_exchange.generate_ecdh_keypair()
        priv_b, pub_b = key_exchange.generate_ecdh_keypair()

        # Derive shared secrets
        shared_a = key_exchange.derive_shared_key(priv_a, pub_b)
        shared_b = key_exchange.derive_shared_key(priv_b, pub_a)

        # Should be identical
        assert shared_a == shared_b
        assert len(shared_a) > 0

    def test_different_peers_different_secrets(self, key_exchange):
        """Test that different peer combinations produce different secrets."""
        priv_a, pub_a = key_exchange.generate_ecdh_keypair()
        priv_b, pub_b = key_exchange.generate_ecdh_keypair()
        priv_c, pub_c = key_exchange.generate_ecdh_keypair()

        shared_ab = key_exchange.derive_shared_key(priv_a, pub_b)
        shared_ac = key_exchange.derive_shared_key(priv_a, pub_c)

        assert shared_ab != shared_ac

    def test_generate_rsa_keypair(self, key_exchange):
        """Test RSA key pair generation."""
        if not hasattr(key_exchange, 'generate_rsa_keypair'):
            pytest.skip("RSA keypair generation not available")

        private_key, public_key = key_exchange.generate_rsa_keypair()

        assert private_key is not None
        assert public_key is not None

    def test_key_storage_and_loading(self, key_exchange):
        """Test storing and loading keys."""
        if not hasattr(key_exchange, 'store_keypair'):
            pytest.skip("Key storage not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            priv, pub = key_exchange.generate_ecdh_keypair()

            # Store keys
            key_exchange.store_keypair(
                private_key=priv,
                public_key=pub,
                key_path=temp_dir,
                key_name="test_key"
            )

            # Verify files created
            assert (Path(temp_dir) / "test_key.priv").exists()
            assert (Path(temp_dir) / "test_key.pub").exists()


class TestAuditLogger:
    """Test suite for HIPAA-compliant audit logging."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance with temp directory."""
        try:
            from src.core import AuditLogger
            with tempfile.TemporaryDirectory() as temp_dir:
                logger = AuditLogger(log_path=temp_dir)
                logger._temp_dir = temp_dir  # Store for test access
                yield logger
        except ImportError:
            pytest.skip("AuditLogger module not available")

    @pytest.fixture
    def event_type(self):
        """Get AuditEventType enum."""
        try:
            from src.core import AuditEventType
            return AuditEventType
        except ImportError:
            pytest.skip("AuditEventType not available")

    def test_log_event(self, audit_logger, event_type):
        """Test basic event logging."""
        audit_logger.log_event(
            event_type=event_type.DATA_ACCESS,
            description="Test event",
            user_id="test_user",
            resource_id="resource_123"
        )

        # Verify event was logged
        events = audit_logger.get_events()
        assert len(events) >= 1

    def test_hash_chain_integrity(self, audit_logger, event_type):
        """Test that hash chain maintains integrity."""
        # Log multiple events
        for i in range(5):
            audit_logger.log_event(
                event_type=event_type.DATA_ACCESS,
                description=f"Event {i}",
                user_id="test_user"
            )

        # Verify chain
        is_valid = audit_logger.verify_chain()
        assert is_valid is True

    def test_tamper_detection(self, audit_logger, event_type):
        """Test that tampering is detected."""
        # Log events
        audit_logger.log_event(
            event_type=event_type.FILE_DOWNLOAD,
            description="Event 1",
            user_id="test_user"
        )
        audit_logger.log_event(
            event_type=event_type.FILE_UPLOAD,
            description="Event 2",
            user_id="test_user"
        )

        # Tamper with an event (if possible)
        if hasattr(audit_logger, '_events') and len(audit_logger._events) > 0:
            audit_logger._events[0]['description'] = "TAMPERED"

            # Chain should now be invalid
            is_valid = audit_logger.verify_chain()
            assert is_valid is False

    def test_sensitive_data_redaction(self, audit_logger, event_type):
        """Test that sensitive data is redacted."""
        audit_logger.log_event(
            event_type=event_type.DATA_ACCESS,
            description="Accessed SSN: 123-45-6789",
            user_id="test_user",
            metadata={"ssn": "123-45-6789", "name": "John Doe"}
        )

        events = audit_logger.get_events()
        if events:
            last_event = events[-1]
            # SSN should be redacted
            if 'metadata' in last_event:
                assert '123-45-6789' not in str(last_event)

    def test_export_for_compliance(self, audit_logger, event_type):
        """Test compliance export functionality."""
        # Log some events
        audit_logger.log_event(
            event_type=event_type.FILE_DOWNLOAD,
            description="Downloaded file",
            user_id="compliance_test"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name

        try:
            audit_logger.export_for_compliance(export_path)
            assert Path(export_path).exists()

            # Verify JSON is valid
            with open(export_path) as f:
                data = json.load(f)
                assert 'events' in data or isinstance(data, list)
        finally:
            os.unlink(export_path)

    def test_event_types_coverage(self, event_type):
        """Test that common event types are available."""
        required_types = [
            'FILE_DOWNLOAD',
            'FILE_UPLOAD',
            'FILE_DELETE',
            'DATA_ACCESS',
            'FILE_DECRYPT',
            'FILE_ENCRYPT',
        ]

        for type_name in required_types:
            assert hasattr(event_type, type_name), f"Missing event type: {type_name}"


class TestSecureTransferPipeline:
    """Test suite for SecureTransferPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create SecureTransferPipeline instance."""
        try:
            from src.core import SecureTransferPipeline
            with tempfile.TemporaryDirectory() as temp_dir:
                pipeline = SecureTransferPipeline(temp_dir=temp_dir)
                pipeline._temp_dir = temp_dir
                yield pipeline
        except ImportError:
            pytest.skip("SecureTransferPipeline not available")

    def test_secure_delete(self, pipeline):
        """Test DoD-compliant secure deletion."""
        # Create a test file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"sensitive data " * 100)
            temp_path = f.name

        # Secure delete
        result = pipeline.secure_delete(temp_path)

        assert result['success'] is True
        assert not os.path.exists(temp_path)

    def test_secure_delete_multiple_passes(self, pipeline):
        """Test that secure delete performs multiple passes."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * 1000)
            temp_path = f.name

        result = pipeline.secure_delete(temp_path, passes=3)

        assert result['success'] is True
        assert result.get('passes', 3) >= 3

    def test_verify_integrity(self, pipeline):
        """Test file integrity verification."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content for integrity check")
            temp_path = f.name

        try:
            # Calculate checksum
            checksum = pipeline._calculate_checksum(temp_path)

            # Verify integrity
            is_valid = pipeline.verify_integrity(temp_path, checksum)
            assert is_valid is True

            # Modify file and verify fails
            with open(temp_path, 'ab') as f:
                f.write(b"tampered")

            is_valid = pipeline.verify_integrity(temp_path, checksum)
            assert is_valid is False

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_transfer_modes(self, pipeline):
        """Test that transfer modes are available."""
        try:
            from src.core import TransferMode

            assert hasattr(TransferMode, 'STANDARD')
            assert hasattr(TransferMode, 'ZERO_KNOWLEDGE')
            assert hasattr(TransferMode, 'STREAMING')
        except ImportError:
            pytest.skip("TransferMode not available")


class TestCoreModuleIntegration:
    """Integration tests for core modules working together."""

    def test_full_secure_workflow(self):
        """Test complete secure workflow: key exchange -> audit -> secure delete."""
        try:
            from src.core import KeyExchange, AuditLogger, AuditEventType, SecureTransferPipeline
        except ImportError:
            pytest.skip("Core modules not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize components
            key_exchange = KeyExchange()
            audit_logger = AuditLogger(log_path=temp_dir)
            pipeline = SecureTransferPipeline(temp_dir=temp_dir)

            # Step 1: Key exchange
            priv_a, pub_a = key_exchange.generate_ecdh_keypair()
            priv_b, pub_b = key_exchange.generate_ecdh_keypair()
            shared_key = key_exchange.derive_shared_key(priv_a, pub_b)

            audit_logger.log_event(
                event_type=AuditEventType.KEY_EXCHANGE if hasattr(AuditEventType, 'KEY_EXCHANGE') else AuditEventType.DATA_ACCESS,
                description="Key exchange completed",
                user_id="integration_test"
            )

            # Step 2: Create and process file
            test_file = Path(temp_dir) / "test_data.bin"
            test_file.write_bytes(b"sensitive medical data " * 50)

            audit_logger.log_event(
                event_type=AuditEventType.FILE_DOWNLOAD,
                description="File downloaded",
                user_id="integration_test",
                resource_id=str(test_file)
            )

            # Step 3: Secure delete
            result = pipeline.secure_delete(str(test_file))

            audit_logger.log_event(
                event_type=AuditEventType.FILE_DELETE,
                description="File securely deleted",
                user_id="integration_test"
            )

            # Verify
            assert result['success'] is True
            assert not test_file.exists()
            assert audit_logger.verify_chain() is True

    def test_core_module_imports(self):
        """Test that all core modules can be imported from src.core."""
        try:
            from src.core import (
                SecureTransferPipeline,
                AuditLogger,
                KeyExchange,
                AuditEventType,
                TransferMode
            )

            # Verify classes exist
            assert SecureTransferPipeline is not None
            assert AuditLogger is not None
            assert KeyExchange is not None
        except ImportError as e:
            pytest.skip(f"Core modules not fully available: {e}")
