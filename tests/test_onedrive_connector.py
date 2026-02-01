"""Tests for Microsoft OneDrive Connector.

These tests use mocking to avoid requiring actual Microsoft credentials.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json


class TestOneDriveConnector:
    """Test suite for OneDriveConnector."""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests module."""
        with patch('src.connectors.onedrive_connector.REQUESTS_AVAILABLE', True):
            with patch('src.connectors.onedrive_connector.requests') as mock_req:
                # Setup session mock
                mock_session = Mock()
                mock_req.Session.return_value = mock_session

                yield mock_req, mock_session

    @pytest.fixture
    def connector(self, mock_requests):
        """Create a connector instance with mocked dependencies."""
        mock_req, mock_session = mock_requests

        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-client-id",
            client_secret="test-secret",
            tenant_id="test-tenant",
            access_token="test-token"
        )

        # Mock successful connection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'drive-123',
            'name': 'Test Drive'
        }
        mock_session.get.return_value = mock_response

        connector._session = mock_session
        connector._connected = True
        connector.drive_id = "drive-123"

        return connector

    def test_init_with_client_credentials(self, mock_requests):
        """Test initialization with client credentials."""
        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            client_secret="test-secret",
            tenant_id="test-tenant"
        )

        assert connector.client_id == "test-id"
        assert connector.client_secret == "test-secret"
        assert connector.tenant_id == "test-tenant"

    def test_init_with_access_token(self, mock_requests):
        """Test initialization with pre-obtained access token."""
        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            access_token="pre-obtained-token"
        )

        assert connector.access_token == "pre-obtained-token"

    def test_connect_success(self, mock_requests):
        """Test successful connection."""
        mock_req, mock_session = mock_requests

        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            access_token="test-token"
        )

        # Mock successful drive info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'drive-123',
            'name': 'OneDrive'
        }
        mock_session.get.return_value = mock_response

        result = connector.connect()

        assert result is True
        assert connector._connected is True
        assert connector.drive_id == 'drive-123'

    def test_connect_failure(self, mock_requests):
        """Test connection failure."""
        mock_req, mock_session = mock_requests

        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            access_token="invalid-token"
        )

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_session.get.return_value = mock_response

        result = connector.connect()

        assert result is False
        assert connector._connected is False

    def test_upload_file_not_connected(self, mock_requests):
        """Test upload fails when not connected."""
        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            access_token="test-token"
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

    def test_upload_small_file_success(self, connector):
        """Test successful small file upload (< 4MB)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"small test content")
            temp_path = f.name

        try:
            # Mock successful upload response
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                'id': 'item-123',
                'webUrl': 'https://onedrive.com/item-123'
            }
            connector._session.put.return_value = mock_response

            result = connector.upload_file(temp_path, "remote/test.txt")

            assert result['success'] is True
            assert result['remote_path'] == "remote/test.txt"
            assert 'item_id' in result

        finally:
            os.unlink(temp_path)

    def test_download_file_success(self, connector):
        """Test successful file download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "downloaded.txt"

            # Mock download response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content.return_value = [b"test content"]
            connector._session.get.return_value = mock_response

            result = connector.download_file("remote/test.txt", str(local_path))

            assert result['success'] is True
            assert local_path.exists()

    def test_download_file_not_found(self, connector):
        """Test download of non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "downloaded.txt"

            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            connector._session.get.return_value = mock_response

            result = connector.download_file("nonexistent.txt", str(local_path))

            assert result['success'] is False
            assert 'not found' in result['error'].lower()

    def test_delete_file_success(self, connector):
        """Test successful file deletion."""
        mock_response = Mock()
        mock_response.status_code = 204
        connector._session.delete.return_value = mock_response

        result = connector.delete_file("remote/test.txt")

        assert result['success'] is True

    def test_delete_file_not_found(self, connector):
        """Test deletion of non-existent file (should succeed)."""
        mock_response = Mock()
        mock_response.status_code = 404
        connector._session.delete.return_value = mock_response

        result = connector.delete_file("nonexistent.txt")

        assert result['success'] is True
        assert 'warning' in result

    def test_list_files(self, connector):
        """Test listing files."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {
                    'name': 'test.txt',
                    'id': 'item-1',
                    'size': 1024,
                    'lastModifiedDateTime': '2024-01-01T00:00:00Z',
                    'webUrl': 'https://onedrive.com/item-1'
                },
                {
                    'name': 'folder',
                    'id': 'item-2',
                    'size': 0,
                    'folder': {},
                    'webUrl': 'https://onedrive.com/item-2'
                }
            ]
        }
        connector._session.get.return_value = mock_response

        files = connector.list_files()

        assert len(files) == 2
        assert files[0]['path'] == 'test.txt'
        assert files[0]['is_folder'] is False
        assert files[1]['is_folder'] is True

    def test_get_file_metadata(self, connector):
        """Test getting file metadata."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'item-123',
            'name': 'test.txt',
            'size': 1024,
            'lastModifiedDateTime': '2024-01-01T00:00:00Z',
            'createdDateTime': '2024-01-01T00:00:00Z',
            'webUrl': 'https://onedrive.com/item-123',
            'file': {
                'mimeType': 'text/plain',
                'hashes': {'sha256Hash': 'abc123'}
            }
        }
        connector._session.get.return_value = mock_response

        result = connector.get_file_metadata("test.txt")

        assert result['success'] is True
        assert result['name'] == 'test.txt'
        assert result['size'] == 1024
        assert result['mime_type'] == 'text/plain'

    def test_create_sharing_link(self, connector):
        """Test creating sharing link."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'link': {
                'webUrl': 'https://onedrive.com/share/abc123'
            }
        }
        connector._session.post.return_value = mock_response

        result = connector.create_sharing_link("test.txt", link_type="view")

        assert result['success'] is True
        assert 'sharing_url' in result

    def test_path_validation(self, connector):
        """Test path validation prevents traversal attacks."""
        result = connector.upload_file("test.txt", "../../../etc/passwd")

        assert result['success'] is False

    def test_disconnect(self, connector):
        """Test disconnect clears connection."""
        result = connector.disconnect()

        assert result is True
        assert connector._connected is False

    def test_credential_cleanup(self, mock_requests):
        """Test that credentials are cleared on deletion."""
        from src.connectors.onedrive_connector import OneDriveConnector

        connector = OneDriveConnector(
            client_id="test-id",
            client_secret="sensitive-secret",
            access_token="sensitive-token"
        )

        # Trigger cleanup
        connector.__del__()

        assert connector.client_secret is None
        assert connector.access_token is None


class TestOneDriveConnectorImportError:
    """Test behavior when dependencies are missing."""

    def test_requests_not_available(self):
        """Test error when requests not installed."""
        with patch('src.connectors.onedrive_connector.REQUESTS_AVAILABLE', False):
            import importlib
            import src.connectors.onedrive_connector as module
            importlib.reload(module)

            if not module.REQUESTS_AVAILABLE:
                with pytest.raises(ImportError, match="requests"):
                    module.OneDriveConnector(
                        client_id="test",
                        access_token="test"
                    )
