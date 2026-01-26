"""
Security tests for path traversal validation in cloud connectors.

These tests ensure that malicious path inputs are properly rejected
to prevent directory traversal attacks.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.connectors.s3_connector import S3Connector
from src.connectors.google_drive_connector import GoogleDriveConnector
from src.connectors.dropbox_connector import DropboxConnector


class TestPathTraversalSecurity:
    """Test suite for path traversal attack prevention."""

    @pytest.fixture
    def s3_connector(self):
        """Create S3 connector instance for testing with mocked client."""
        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            mock_s3 = Mock()
            mock_s3.head_bucket.return_value = True
            mock_s3.upload_file.return_value = None
            mock_s3.download_file.return_value = None
            mock_s3.delete_object.return_value = {}
            mock_s3.head_object.return_value = {'ContentLength': 100, 'Metadata': {}}
            mock_s3.list_objects_v2.return_value = {'Contents': []}
            mock_client.return_value = mock_s3
            mock_resource.return_value = Mock()

            connector = S3Connector(
                bucket_name="test-bucket",
                access_key="test",
                secret_key="test",
                region="us-east-1"
            )
            connector.connect()
            # Store mock for validation
            connector.s3_client = mock_s3
            yield connector

    @pytest.fixture
    def gdrive_connector(self, tmp_path):
        """Create Google Drive connector instance for testing."""
        # Create a minimal credentials file
        creds_file = tmp_path / "gdrive_creds.json"
        creds_file.write_text('{"type": "service_account"}')

        connector = GoogleDriveConnector(credentials_path=str(creds_file))
        connector._connected = True
        connector._service = Mock()
        return connector

    @pytest.fixture
    def dropbox_connector(self):
        """Create Dropbox connector instance for testing."""
        with patch('dropbox.Dropbox') as mock_dbx_class:
            mock_dbx = Mock()
            mock_dbx.users_get_current_account.return_value = Mock()
            mock_dbx.files_upload.return_value = Mock()
            mock_dbx.files_download_to_file.return_value = None
            mock_dbx_class.return_value = mock_dbx

            connector = DropboxConnector(access_token="fake_token")
            connector._connected = True
            connector._dbx = mock_dbx
            yield connector

    # Test cases for malicious paths
    malicious_paths = [
        "../../../etc/passwd",           # Parent directory traversal
        "..\\..\\..\\windows\\system32",  # Windows-style traversal
        "../../sensitive_data",           # Relative parent paths
        "/etc/shadow",                     # Absolute Unix path
        "C:\\Windows\\System32",           # Absolute Windows path
        "D:\\secrets\\data",               # Another Windows absolute path
        "folder/../../../etc/passwd",     # Mixed valid and traversal
        "test\x00file",                    # Null byte injection
        "test\nfile",                      # Newline injection
        "test\rfile",                      # Carriage return injection
        "test\tfile",                      # Tab injection
        "",                                 # Empty string
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd", # URL encoded ../../../etc/passwd
        "..%2f..%2fetc%2fpasswd",         # Partially URL encoded
        "%2e%2e%5c%2e%2e%5cWindows",      # URL encoded ..\..\Windows
        "..%252f..%252fetc",               # Double URL encoded
        "%252e%252e%252f%252e%252e",      # Double encoded ../..
    ]

    # Test cases for valid paths
    valid_paths = [
        "documents/report.pdf",
        "images/photo.jpg",
        "backup/2024/data.zip",
        "simple_file.txt",
        "folder/subfolder/file.doc",
    ]

    def test_s3_upload_rejects_malicious_paths(self, s3_connector, tmp_path):
        """Test that S3 connector rejects malicious paths in upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        for malicious_path in self.malicious_paths:
            result = s3_connector.upload_file(test_file, malicious_path)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result
            assert any(keyword in result['error'].lower()
                      for keyword in ['invalid', 'traversal', 'absolute', 'path', 'empty'])

    def test_s3_download_rejects_malicious_paths(self, s3_connector, tmp_path):
        """Test that S3 connector rejects malicious paths in download."""
        local_file = tmp_path / "download.txt"

        for malicious_path in self.malicious_paths:
            result = s3_connector.download_file(malicious_path, local_file)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_s3_delete_rejects_malicious_paths(self, s3_connector):
        """Test that S3 connector rejects malicious paths in delete."""
        for malicious_path in self.malicious_paths:
            result = s3_connector.delete_file(malicious_path)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_s3_metadata_rejects_malicious_paths(self, s3_connector):
        """Test that S3 connector rejects malicious paths in metadata retrieval."""
        for malicious_path in self.malicious_paths:
            result = s3_connector.get_file_metadata(malicious_path)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_gdrive_upload_rejects_malicious_paths(self, gdrive_connector, tmp_path):
        """Test that Google Drive connector rejects malicious paths in upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        for malicious_path in self.malicious_paths:
            result = gdrive_connector.upload_file(test_file, malicious_path)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_gdrive_download_rejects_malicious_paths(self, gdrive_connector, tmp_path):
        """Test that Google Drive connector rejects malicious paths in download."""
        local_file = tmp_path / "download.txt"

        for malicious_path in self.malicious_paths:
            result = gdrive_connector.download_file(malicious_path, local_file)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_dropbox_upload_rejects_malicious_paths(self, dropbox_connector, tmp_path):
        """Test that Dropbox connector rejects malicious paths in upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        for malicious_path in self.malicious_paths:
            result = dropbox_connector.upload_file(test_file, malicious_path)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_dropbox_download_rejects_malicious_paths(self, dropbox_connector, tmp_path):
        """Test that Dropbox connector rejects malicious paths in download."""
        local_file = tmp_path / "download.txt"

        for malicious_path in self.malicious_paths:
            result = dropbox_connector.download_file(malicious_path, local_file)
            assert result['success'] is False, f"Should reject path: {malicious_path}"
            assert 'error' in result

    def test_all_connectors_accept_valid_paths(self, tmp_path):
        """Test that all connectors accept valid paths (won't fail validation)."""
        from src.connectors.base_connector import CloudConnector

        # Create a test connector that just validates paths
        class TestConnector(CloudConnector):
            def connect(self): return True
            def disconnect(self): return True
            def upload_file(self, file_path, remote_path, metadata=None): pass
            def download_file(self, remote_path, local_path, verify_checksum=True): pass
            def delete_file(self, remote_path): pass
            def list_files(self, prefix=''): pass
            def get_file_metadata(self, remote_path): pass

        connector = TestConnector()

        # Valid paths should NOT raise validation errors
        for valid_path in self.valid_paths:
            try:
                connector._validate_remote_path(valid_path)
            except ValueError as e:
                pytest.fail(f"Valid path '{valid_path}' was rejected: {e}")

    def test_base_connector_validate_remote_path_direct(self):
        """Test the _validate_remote_path method directly."""
        from src.connectors.base_connector import CloudConnector

        # Create a concrete implementation for testing
        class TestConnector(CloudConnector):
            def connect(self): return True
            def disconnect(self): return True
            def upload_file(self, file_path, remote_path, metadata=None): pass
            def download_file(self, remote_path, local_path, verify_checksum=True): pass
            def delete_file(self, remote_path): pass
            def list_files(self, prefix=''): pass
            def get_file_metadata(self, remote_path): pass

        connector = TestConnector()

        # Valid paths should not raise
        for valid_path in self.valid_paths:
            try:
                connector._validate_remote_path(valid_path)
            except ValueError:
                pytest.fail(f"Valid path rejected: {valid_path}")

        # Invalid paths should raise ValueError
        for malicious_path in self.malicious_paths:
            with pytest.raises(ValueError):
                connector._validate_remote_path(malicious_path)

    def test_path_validation_prevents_real_world_attacks(self):
        """Test against real-world attack patterns."""
        from src.connectors.base_connector import CloudConnector

        class TestConnector(CloudConnector):
            def connect(self): return True
            def disconnect(self): return True
            def upload_file(self, file_path, remote_path, metadata=None): pass
            def download_file(self, remote_path, local_path, verify_checksum=True): pass
            def delete_file(self, remote_path): pass
            def list_files(self, prefix=''): pass
            def get_file_metadata(self, remote_path): pass

        connector = TestConnector()

        real_world_attacks = [
            # URL encoding attacks
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # ../../../etc/passwd encoded
            # Double encoding
            "..%252f..%252fetc%252fpasswd",
            # Unicode encoding
            "..%c0%af..%c0%afetc%c0%afpasswd",
            # Mixed separators
            "..//../../etc/passwd",
            "..\\..\\etc\\passwd",
        ]

        for attack in real_world_attacks:
            # These might not all be caught by current implementation,
            # but documenting expected behavior
            with pytest.raises(ValueError):
                connector._validate_remote_path(attack)
