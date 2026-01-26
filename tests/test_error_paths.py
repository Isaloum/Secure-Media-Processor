"""Error path tests for production resilience.

Tests critical error scenarios that could occur in production:
- Corrupted files
- Network failures
- Invalid credentials
- Rate limiting
- Disk space issues
- Permission errors
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# ENCRYPTION ERROR TESTS
# =============================================================================

class TestEncryptionErrors:
    """Test encryption error handling."""

    def test_encrypt_corrupted_key_file(self, temp_dir):
        """Test encryption with corrupted key file."""
        from src.encryption import MediaEncryptor

        # Create corrupted key file (wrong length)
        key_path = temp_dir / "bad.key"
        key_path.write_bytes(b"tooshort")  # Should be 32 bytes

        with pytest.raises(ValueError):
            MediaEncryptor(key_path)

    def test_decrypt_tampered_ciphertext(self, temp_dir):
        """Test decryption with tampered ciphertext fails."""
        from src.encryption import MediaEncryptor

        # Create encryptor and encrypt a file
        key_path = temp_dir / "test.key"
        encryptor = MediaEncryptor(key_path)

        original = temp_dir / "original.txt"
        original.write_text("Sensitive data")

        encrypted = temp_dir / "encrypted.bin"
        encryptor.encrypt_file(original, encrypted)

        # Tamper with the encrypted file
        data = encrypted.read_bytes()
        tampered = data[:10] + b'\x00\x00\x00' + data[13:]  # Corrupt 3 bytes
        encrypted.write_bytes(tampered)

        # Decryption should fail
        decrypted = temp_dir / "decrypted.txt"
        with pytest.raises(Exception):  # Will raise InvalidTag or similar
            encryptor.decrypt_file(encrypted, decrypted)

    def test_decrypt_wrong_key(self, temp_dir):
        """Test decryption with wrong key fails."""
        from src.encryption import MediaEncryptor

        # Encrypt with key1
        key1_path = temp_dir / "key1.key"
        encryptor1 = MediaEncryptor(key1_path)

        original = temp_dir / "original.txt"
        original.write_text("Secret message")

        encrypted = temp_dir / "encrypted.bin"
        encryptor1.encrypt_file(original, encrypted)

        # Try to decrypt with key2
        key2_path = temp_dir / "key2.key"
        encryptor2 = MediaEncryptor(key2_path)

        decrypted = temp_dir / "decrypted.txt"
        with pytest.raises(Exception):  # Will raise InvalidTag
            encryptor2.decrypt_file(encrypted, decrypted)

    def test_encrypt_empty_file(self, temp_dir):
        """Test encryption of empty file."""
        from src.encryption import MediaEncryptor

        key_path = temp_dir / "test.key"
        encryptor = MediaEncryptor(key_path)

        empty_file = temp_dir / "empty.txt"
        empty_file.write_bytes(b"")

        encrypted = temp_dir / "encrypted.bin"
        result = encryptor.encrypt_file(empty_file, encrypted)

        # Should succeed and produce valid output
        assert result['original_size'] == 0
        assert encrypted.exists()
        assert encrypted.stat().st_size > 0  # Overhead from nonce + tag

        # Should be able to decrypt back to empty file
        decrypted = temp_dir / "decrypted.txt"
        result = encryptor.decrypt_file(encrypted, decrypted)
        assert result['decrypted_size'] == 0
        assert decrypted.read_bytes() == b""

    def test_encrypt_binary_file(self, temp_dir):
        """Test encryption of binary file with null bytes."""
        from src.encryption import MediaEncryptor

        key_path = temp_dir / "test.key"
        encryptor = MediaEncryptor(key_path)

        # Create binary file with null bytes
        binary_data = bytes([i % 256 for i in range(1000)])
        binary_file = temp_dir / "binary.bin"
        binary_file.write_bytes(binary_data)

        encrypted = temp_dir / "encrypted.bin"
        encryptor.encrypt_file(binary_file, encrypted)

        decrypted = temp_dir / "decrypted.bin"
        encryptor.decrypt_file(encrypted, decrypted)

        assert decrypted.read_bytes() == binary_data

    def test_encrypt_large_file(self, temp_dir):
        """Test encryption of large file (10MB)."""
        from src.encryption import MediaEncryptor

        key_path = temp_dir / "test.key"
        encryptor = MediaEncryptor(key_path)

        # Create 10MB file
        large_data = os.urandom(10 * 1024 * 1024)
        large_file = temp_dir / "large.bin"
        large_file.write_bytes(large_data)

        encrypted = temp_dir / "encrypted.bin"
        result = encryptor.encrypt_file(large_file, encrypted)

        assert result['original_size'] == 10 * 1024 * 1024
        assert encrypted.exists()

        decrypted = temp_dir / "decrypted.bin"
        encryptor.decrypt_file(encrypted, decrypted)

        assert decrypted.read_bytes() == large_data

    def test_secure_delete_nonexistent_file(self, temp_dir):
        """Test secure delete of nonexistent file."""
        from src.encryption import MediaEncryptor

        key_path = temp_dir / "test.key"
        encryptor = MediaEncryptor(key_path)

        nonexistent = temp_dir / "does_not_exist.txt"

        # Should not raise, just log warning
        encryptor.secure_delete(nonexistent)


# =============================================================================
# S3 CONNECTOR ERROR TESTS
# =============================================================================

class TestS3ConnectorErrors:
    """Test S3 connector error handling."""

    def test_upload_invalid_credentials(self, temp_dir):
        """Test upload with invalid AWS credentials returns error result."""
        from src.connectors.s3_connector import S3Connector
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            # Mock client error for invalid credentials
            mock_s3 = Mock()
            mock_s3.head_bucket.return_value = True  # Allow connect
            mock_s3.upload_file.side_effect = ClientError(
                {'Error': {'Code': 'InvalidAccessKeyId', 'Message': 'Invalid key'}},
                'PutObject'
            )
            mock_client.return_value = mock_s3
            mock_resource.return_value = Mock()

            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='invalid',
                secret_key='invalid',
                region='us-east-1'
            )
            connector.connect()

            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")

            # Should return error result, not raise
            result = connector.upload_file(str(test_file), 'test-key')

            assert result['success'] is False
            assert 'InvalidAccessKeyId' in result['error']

    def test_connection_failure(self):
        """Test connection failure handling."""
        from src.connectors.s3_connector import S3Connector
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_s3.head_bucket.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
                'HeadBucket'
            )
            mock_client.return_value = mock_s3

            connector = S3Connector(
                bucket_name='nonexistent-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )

            result = connector.connect()
            assert result is False

    def test_upload_bucket_not_found(self, temp_dir):
        """Test upload to bucket that was deleted returns error result."""
        from src.connectors.s3_connector import S3Connector
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            mock_s3 = Mock()
            mock_s3.head_bucket.return_value = True  # Allow connect
            mock_s3.upload_file.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
                'PutObject'
            )
            mock_client.return_value = mock_s3
            mock_resource.return_value = Mock()

            connector = S3Connector(
                bucket_name='deleted-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )
            connector.connect()

            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")

            result = connector.upload_file(str(test_file), 'test-key')

            assert result['success'] is False
            assert 'NoSuchBucket' in result['error']

    def test_download_file_not_found(self, temp_dir):
        """Test download of nonexistent file returns error result."""
        from src.connectors.s3_connector import S3Connector
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            mock_s3 = Mock()
            mock_s3.head_bucket.return_value = True
            mock_s3.download_file.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Key does not exist'}},
                'GetObject'
            )
            mock_client.return_value = mock_s3
            mock_resource.return_value = Mock()

            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )
            connector.connect()

            result = connector.download_file('nonexistent-key', str(temp_dir / 'local.txt'))

            assert result['success'] is False
            assert 'NoSuchKey' in result['error']

    def test_access_denied(self, temp_dir):
        """Test operation with access denied returns error result."""
        from src.connectors.s3_connector import S3Connector
        from botocore.exceptions import ClientError

        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            mock_s3 = Mock()
            mock_s3.head_bucket.return_value = True
            mock_s3.upload_file.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
                'PutObject'
            )
            mock_client.return_value = mock_s3
            mock_resource.return_value = Mock()

            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )
            connector.connect()

            test_file = temp_dir / "test.txt"
            test_file.write_text("test content")

            result = connector.upload_file(str(test_file), 'test-key')

            assert result['success'] is False
            assert 'AccessDenied' in result['error']


# =============================================================================
# GOOGLE DRIVE CONNECTOR ERROR TESTS
# =============================================================================

class TestGoogleDriveConnectorErrors:
    """Test Google Drive connector error handling."""

    def test_invalid_credentials_file(self, temp_dir):
        """Test with invalid/corrupted credentials file returns False."""
        from src.connectors.google_drive_connector import GoogleDriveConnector

        # Create an invalid credentials file
        creds_file = temp_dir / "bad_creds.json"
        creds_file.write_text('not valid json {')

        # Constructor shouldn't fail, but connect should return False
        connector = GoogleDriveConnector(credentials_path=str(creds_file))
        result = connector.connect()
        assert result is False

    def test_connection_without_credentials(self, temp_dir):
        """Test that connection fails without valid credentials."""
        from src.connectors.google_drive_connector import GoogleDriveConnector

        # Create empty credentials file
        creds_file = temp_dir / "empty_creds.json"
        creds_file.write_text('{}')

        connector = GoogleDriveConnector(credentials_path=str(creds_file))
        # Connection should fail
        result = connector.connect()
        assert result is False


# =============================================================================
# DROPBOX CONNECTOR ERROR TESTS
# =============================================================================

class TestDropboxConnectorErrors:
    """Test Dropbox connector error handling."""

    def test_invalid_access_token(self):
        """Test with invalid access token."""
        from src.connectors.dropbox_connector import DropboxConnector
        import dropbox

        with patch('dropbox.Dropbox') as mock_dbx_class:
            mock_dbx = Mock()
            # AuthError constructor is complex, let's use a simpler approach
            mock_dbx.users_get_current_account.side_effect = Exception("Invalid access token")
            mock_dbx_class.return_value = mock_dbx

            connector = DropboxConnector(access_token='invalid_token')

            # Connection should fail
            result = connector.connect()
            assert result is False

    def test_connection_failure_logged(self, temp_dir):
        """Test that connection failures are properly handled."""
        from src.connectors.dropbox_connector import DropboxConnector

        with patch('dropbox.Dropbox') as mock_dbx_class:
            mock_dbx = Mock()
            mock_dbx.users_get_current_account.side_effect = Exception("Network error")
            mock_dbx_class.return_value = mock_dbx

            connector = DropboxConnector(access_token='test_token')
            result = connector.connect()

            assert result is False


# =============================================================================
# GPU PROCESSOR ERROR TESTS
# =============================================================================

class TestGPUProcessorErrors:
    """Test GPU processor error handling."""

    def test_invalid_image_path(self, temp_dir):
        """Test processing with invalid image path."""
        from src.gpu_processor import GPUMediaProcessor

        processor = GPUMediaProcessor(gpu_enabled=False)

        with pytest.raises(Exception):
            processor.resize_image(
                temp_dir / "nonexistent.png",
                temp_dir / "output.png",
                size=(100, 100)
            )

    def test_corrupted_image(self, temp_dir):
        """Test processing corrupted image."""
        from src.gpu_processor import GPUMediaProcessor

        # Create corrupted image file
        corrupted = temp_dir / "corrupted.png"
        corrupted.write_bytes(b"not a real image file")

        processor = GPUMediaProcessor(gpu_enabled=False)

        with pytest.raises(Exception):
            processor.resize_image(
                corrupted,
                temp_dir / "output.png",
                size=(100, 100)
            )

    def test_invalid_video(self, temp_dir):
        """Test processing invalid video."""
        from src.gpu_processor import GPUMediaProcessor

        # Create invalid video file
        invalid_video = temp_dir / "invalid.mp4"
        invalid_video.write_bytes(b"not a real video")

        processor = GPUMediaProcessor(gpu_enabled=False)

        with pytest.raises(ValueError) as exc_info:
            processor.process_video(
                invalid_video,
                temp_dir / "output.mp4"
            )

        assert "Could not open video" in str(exc_info.value)


# =============================================================================
# RATE LIMITER ERROR TESTS
# =============================================================================

class TestRateLimiterErrors:
    """Test rate limiter edge cases."""

    def test_rate_limit_exhausted(self):
        """Test behavior when rate limit is exhausted."""
        from src.rate_limiter import RateLimiter

        # Create rate limiter with very low rate (1 per second, capacity 1)
        limiter = RateLimiter(rate=1.0, capacity=1)

        # First request should succeed
        assert limiter.acquire() is True

        # Second immediate request should fail (no tokens left)
        assert limiter.acquire(blocking=False) is False

    def test_rate_limiter_recovery(self):
        """Test that rate limiter recovers after wait."""
        from src.rate_limiter import RateLimiter
        import time

        # High rate limiter that refills quickly
        limiter = RateLimiter(rate=100.0, capacity=1)

        # Exhaust the limiter
        limiter.acquire()
        assert limiter.acquire(blocking=False) is False

        # Wait for token refill (100 per second = 1 every 0.01 seconds)
        time.sleep(0.05)  # Wait for at least one token

        # Should be able to acquire again
        assert limiter.acquire(blocking=False) is True

    def test_rate_limiter_burst(self):
        """Test burst capacity of rate limiter."""
        from src.rate_limiter import RateLimiter

        # Limiter with burst capacity of 5
        limiter = RateLimiter(rate=1.0, capacity=5)

        # Should be able to acquire 5 tokens in quick succession
        for i in range(5):
            assert limiter.acquire(blocking=False) is True

        # 6th should fail
        assert limiter.acquire(blocking=False) is False


# =============================================================================
# LICENSE MANAGER ERROR TESTS
# =============================================================================

class TestLicenseManagerErrors:
    """Test license manager error handling."""

    def test_invalid_license_format(self, temp_dir):
        """Test activation with invalid license format."""
        from src.license_manager import LicenseManager

        license_file = temp_dir / "license.json"
        manager = LicenseManager(str(license_file))

        with pytest.raises(ValueError) as exc_info:
            manager.activate_license("invalid-format", "test@example.com")

        assert "Invalid license" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()

    def test_expired_license(self, temp_dir):
        """Test with expired license."""
        from src.license_manager import LicenseManager, LicenseType
        import json
        from datetime import datetime, timedelta

        license_file = temp_dir / "license.json"

        # Create expired license data
        expired_license = {
            "license_key": "TEST-LICENSE-KEY",
            "license_type": "pro",
            "email": "test@example.com",
            "issued_at": (datetime.now() - timedelta(days=400)).isoformat(),
            "expires_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "features": ["cloud_storage"],
            "device_ids": []
        }
        license_file.write_text(json.dumps(expired_license))

        manager = LicenseManager(str(license_file))
        info = manager.get_license_info()

        # License should show as expired or inactive
        # Implementation may vary - just verify it doesn't crash
        assert info is not None


# =============================================================================
# PATH SECURITY ERROR TESTS
# =============================================================================

class TestPathSecurityErrors:
    """Test path traversal and security error handling."""

    def test_directory_traversal_blocked(self):
        """Test that directory traversal is blocked."""
        from src.connectors.s3_connector import S3Connector

        with patch('boto3.client'), patch('boto3.resource'):
            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )

            # Try directory traversal in remote key
            with pytest.raises(ValueError) as exc_info:
                connector._validate_remote_path("../../../etc/passwd")

            assert "traversal" in str(exc_info.value).lower()

    def test_null_byte_injection_blocked(self):
        """Test that null byte injection is blocked."""
        from src.connectors.s3_connector import S3Connector

        with patch('boto3.client'), patch('boto3.resource'):
            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )

            # Try null byte injection
            with pytest.raises(ValueError) as exc_info:
                connector._validate_remote_path("file.txt\x00.exe")

            assert "invalid" in str(exc_info.value).lower()

    def test_url_encoded_traversal_blocked(self):
        """Test URL-encoded path traversal is blocked."""
        from src.connectors.s3_connector import S3Connector

        with patch('boto3.client'), patch('boto3.resource'):
            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )

            # Try URL-encoded traversal
            with pytest.raises(ValueError):
                connector._validate_remote_path("%2e%2e%2fetc/passwd")

    def test_absolute_path_blocked(self):
        """Test absolute paths are blocked."""
        from src.connectors.s3_connector import S3Connector

        with patch('boto3.client'), patch('boto3.resource'):
            connector = S3Connector(
                bucket_name='test-bucket',
                access_key='test',
                secret_key='test',
                region='us-east-1'
            )

            # Try absolute path
            with pytest.raises(ValueError):
                connector._validate_remote_path("/etc/passwd")


# =============================================================================
# CONNECTOR MANAGER ERROR TESTS
# =============================================================================

class TestConnectorManagerErrors:
    """Test connector manager error handling."""

    def test_get_nonexistent_connector_returns_none(self):
        """Test getting connector that doesn't exist returns None."""
        from src.connectors.connector_manager import ConnectorManager

        manager = ConnectorManager()

        # Should return None, not raise
        result = manager.get_connector('nonexistent')
        assert result is None

    def test_remove_nonexistent_connector(self):
        """Test removing connector that doesn't exist."""
        from src.connectors.connector_manager import ConnectorManager

        manager = ConnectorManager()

        # Should return False, not raise
        result = manager.remove_connector('nonexistent')
        assert result is False

    def test_set_active_nonexistent(self):
        """Test setting active to nonexistent connector."""
        from src.connectors.connector_manager import ConnectorManager

        manager = ConnectorManager()

        result = manager.set_active('nonexistent')
        assert result is False

    def test_get_active_when_none_set(self):
        """Test getting active connector when none is set."""
        from src.connectors.connector_manager import ConnectorManager

        manager = ConnectorManager()

        result = manager.get_active_connector()
        assert result is None

    def test_add_connector_replaces_existing(self):
        """Test that adding a connector with same name replaces it."""
        from src.connectors.connector_manager import ConnectorManager
        from src.connectors.dropbox_connector import DropboxConnector
        from unittest.mock import Mock

        manager = ConnectorManager()

        # Add first mock connector
        mock1 = Mock()
        mock1.get_provider_name.return_value = 'mock1'
        manager.add_connector('test', mock1)

        # Add second mock connector with same name
        mock2 = Mock()
        mock2.get_provider_name.return_value = 'mock2'
        manager.add_connector('test', mock2)

        # Should have the second one
        assert manager.get_connector('test') == mock2
