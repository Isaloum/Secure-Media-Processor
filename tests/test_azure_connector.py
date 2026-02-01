"""Tests for Azure Blob Storage Connector.

These tests use mocking to avoid requiring actual Azure credentials.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


class TestAzureBlobConnector:
    """Test suite for AzureBlobConnector."""

    @pytest.fixture
    def mock_azure_imports(self):
        """Mock Azure SDK imports."""
        with patch.dict('sys.modules', {
            'azure': Mock(),
            'azure.storage': Mock(),
            'azure.storage.blob': Mock(),
            'azure.core': Mock(),
            'azure.core.exceptions': Mock(),
        }):
            yield

    @pytest.fixture
    def connector(self, mock_azure_imports):
        """Create a connector instance with mocked Azure SDK."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            with patch('src.connectors.azure_blob_connector.BlobServiceClient') as mock_client:
                # Setup mock
                mock_container = Mock()
                mock_container.exists.return_value = True
                mock_client.from_connection_string.return_value.get_container_client.return_value = mock_container

                from src.connectors.azure_blob_connector import AzureBlobConnector

                connector = AzureBlobConnector(
                    container_name="test-container",
                    connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net"
                )
                connector._connected = True
                connector.container_client = mock_container

                yield connector

    def test_init_with_connection_string(self, mock_azure_imports):
        """Test initialization with connection string."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            from src.connectors.azure_blob_connector import AzureBlobConnector

            connector = AzureBlobConnector(
                container_name="test-container",
                connection_string="DefaultEndpointsProtocol=https;..."
            )

            assert connector.container_name == "test-container"
            assert connector.connection_string == "DefaultEndpointsProtocol=https;..."

    def test_init_with_account_key(self, mock_azure_imports):
        """Test initialization with account name and key."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            from src.connectors.azure_blob_connector import AzureBlobConnector

            connector = AzureBlobConnector(
                container_name="test-container",
                account_name="testaccount",
                account_key="testkey123"
            )

            assert connector.account_name == "testaccount"
            assert connector.account_key == "testkey123"

    def test_init_requires_auth(self, mock_azure_imports):
        """Test that initialization requires authentication method."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            from src.connectors.azure_blob_connector import AzureBlobConnector

            with pytest.raises(ValueError, match="Must provide either"):
                AzureBlobConnector(container_name="test-container")

    def test_init_account_name_requires_key(self, mock_azure_imports):
        """Test that account_name requires account_key or sas_token."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            from src.connectors.azure_blob_connector import AzureBlobConnector

            with pytest.raises(ValueError, match="must also provide"):
                AzureBlobConnector(
                    container_name="test-container",
                    account_name="testaccount"
                )

    def test_upload_file_not_connected(self, mock_azure_imports):
        """Test upload fails when not connected."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', True):
            from src.connectors.azure_blob_connector import AzureBlobConnector

            connector = AzureBlobConnector(
                container_name="test",
                connection_string="test"
            )

            result = connector.upload_file("test.txt", "remote/test.txt")

            assert result['success'] is False
            assert 'Not connected' in result['error']

    def test_upload_file_not_found(self, connector):
        """Test upload with non-existent file."""
        result = connector.upload_file(
            "/nonexistent/file.txt",
            "remote/file.txt"
        )

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_upload_file_success(self, connector):
        """Test successful file upload."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # Mock blob client
            mock_blob = Mock()
            connector.container_client.get_blob_client.return_value = mock_blob

            result = connector.upload_file(temp_path, "remote/test.txt")

            assert result['success'] is True
            assert result['remote_path'] == "remote/test.txt"
            assert 'checksum' in result
            mock_blob.upload_blob.assert_called_once()

        finally:
            os.unlink(temp_path)

    def test_download_file_success(self, connector):
        """Test successful file download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "downloaded.txt"

            # Mock blob client and download
            mock_blob = Mock()
            mock_properties = Mock()
            mock_properties.metadata = {'checksum': 'abc123'}
            mock_blob.get_blob_properties.return_value = mock_properties

            mock_stream = Mock()
            mock_stream.readall.return_value = b"test content"
            mock_blob.download_blob.return_value = mock_stream

            connector.container_client.get_blob_client.return_value = mock_blob

            result = connector.download_file("remote/test.txt", str(local_path))

            assert result['success'] is True
            assert local_path.exists()

    def test_delete_file_success(self, connector):
        """Test successful file deletion."""
        mock_blob = Mock()
        connector.container_client.get_blob_client.return_value = mock_blob

        result = connector.delete_file("remote/test.txt")

        assert result['success'] is True
        mock_blob.delete_blob.assert_called_once()

    def test_list_files(self, connector):
        """Test listing files."""
        mock_blob = Mock()
        mock_blob.name = "test.txt"
        mock_blob.size = 1024
        mock_blob.last_modified = None
        mock_blob.etag = '"abc123"'
        mock_blob.content_settings = None

        connector.container_client.list_blobs.return_value = [mock_blob]

        files = connector.list_files()

        assert len(files) == 1
        assert files[0]['path'] == "test.txt"
        assert files[0]['size'] == 1024

    def test_path_validation(self, connector):
        """Test path validation prevents traversal attacks."""
        result = connector.upload_file("test.txt", "../../../etc/passwd")

        assert result['success'] is False
        assert 'traversal' in result['error'].lower() or 'invalid' in result['error'].lower()

    def test_disconnect(self, connector):
        """Test disconnect clears connection."""
        result = connector.disconnect()

        assert result is True
        assert connector._connected is False


class TestAzureConnectorImportError:
    """Test behavior when Azure SDK is not installed."""

    def test_import_error_when_sdk_missing(self):
        """Test ImportError raised when azure-storage-blob not installed."""
        with patch('src.connectors.azure_blob_connector.AZURE_AVAILABLE', False):
            # Re-import to trigger the error
            import importlib
            import src.connectors.azure_blob_connector as module
            importlib.reload(module)

            if not module.AZURE_AVAILABLE:
                with pytest.raises(ImportError, match="azure-storage-blob"):
                    module.AzureBlobConnector(
                        container_name="test",
                        connection_string="test"
                    )
