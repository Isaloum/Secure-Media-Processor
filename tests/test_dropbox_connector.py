"""Test suite for Dropbox connector."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Mock the dropbox module at import time
sys.modules['dropbox'] = MagicMock()
sys.modules['dropbox.files'] = MagicMock()
sys.modules['dropbox.exceptions'] = MagicMock()

from src.connectors.dropbox_connector import DropboxConnector


@pytest.fixture
def mock_dropbox():
    """Create a mock Dropbox SDK."""
    # The module is already mocked at import time
    return sys.modules['dropbox']


@pytest.fixture
def dropbox_connector():
    """Create Dropbox connector instance."""
    return DropboxConnector(
        access_token='test-token',
        root_path='/TestRoot'
    )


def test_dropbox_connector_initialization():
    """Test Dropbox connector initialization."""
    connector = DropboxConnector(
        access_token='my-token',
        root_path='/MyFolder'
    )
    
    assert connector.access_token == 'my-token'
    assert connector.root_path == '/MyFolder'
    assert not connector.is_connected()


def test_connect_success(dropbox_connector, mock_dropbox):
    """Test successful connection to Dropbox."""
    mock_client = Mock()
    mock_dropbox.Dropbox.return_value = mock_client
    
    result = dropbox_connector.connect()
    
    assert result is True
    assert dropbox_connector.is_connected()
    mock_client.users_get_current_account.assert_called_once()


def test_connect_failure(dropbox_connector, mock_dropbox):
    """Test failed connection to Dropbox."""
    mock_client = Mock()
    mock_client.users_get_current_account.side_effect = Exception("Auth failed")
    mock_dropbox.Dropbox.return_value = mock_client
    
    result = dropbox_connector.connect()
    
    assert result is False
    assert not dropbox_connector.is_connected()


def test_disconnect(dropbox_connector):
    """Test disconnection from Dropbox."""
    dropbox_connector._connected = True
    dropbox_connector.dbx = Mock()
    
    result = dropbox_connector.disconnect()
    
    assert result is True
    assert not dropbox_connector.is_connected()
    assert dropbox_connector.dbx is None


def test_upload_file_not_connected(dropbox_connector, tmp_path):
    """Test upload when not connected."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = dropbox_connector.upload_file(test_file, "test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_upload_file_not_found(dropbox_connector, mock_dropbox):
    """Test upload with non-existent file."""
    dropbox_connector._connected = True
    dropbox_connector.dbx = Mock()
    
    result = dropbox_connector.upload_file("/nonexistent/file.txt", "test.txt")
    
    assert result['success'] is False
    assert 'File not found' in result['error']


def test_upload_file_success(dropbox_connector, tmp_path, mock_dropbox):
    """Test successful file upload."""
    mock_client = Mock()
    mock_upload_result = Mock()
    mock_upload_result.path_display = '/TestRoot/test.txt'
    mock_upload_result.size = 12
    mock_upload_result.client_modified = MagicMock()
    mock_client.files_upload.return_value = mock_upload_result
    
    dropbox_connector._connected = True
    dropbox_connector.dbx = mock_client
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = dropbox_connector.upload_file(test_file, "test.txt")
    
    assert result['success'] is True
    assert result['remote_path'] == '/TestRoot/test.txt'
    assert 'checksum' in result
    assert result['size'] == 12
    mock_client.files_upload.assert_called_once()


def test_download_file_not_connected(dropbox_connector, tmp_path):
    """Test download when not connected."""
    local_path = tmp_path / "downloaded.txt"
    
    result = dropbox_connector.download_file("test.txt", local_path)
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_download_file_success(dropbox_connector, tmp_path, mock_dropbox):
    """Test successful file download."""
    mock_client = Mock()
    mock_metadata = Mock()
    mock_metadata.content_hash = 'abc123'
    mock_response = Mock()
    mock_response.content = b"test content"
    mock_client.files_download.return_value = (mock_metadata, mock_response)
    
    dropbox_connector._connected = True
    dropbox_connector.dbx = mock_client
    
    local_path = tmp_path / "downloaded.txt"
    
    result = dropbox_connector.download_file("test.txt", local_path)
    
    assert result['success'] is True
    assert result['checksum_verified'] is True
    assert local_path.exists()
    assert local_path.read_text() == "test content"


def test_delete_file_not_connected(dropbox_connector):
    """Test delete when not connected."""
    result = dropbox_connector.delete_file("test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_delete_file_success(dropbox_connector, mock_dropbox):
    """Test successful file deletion."""
    mock_client = Mock()
    dropbox_connector._connected = True
    dropbox_connector.dbx = mock_client
    
    result = dropbox_connector.delete_file("test.txt")
    
    assert result['success'] is True
    assert '/TestRoot/test.txt' in result['remote_path']
    mock_client.files_delete_v2.assert_called_once()


def test_list_files_not_connected(dropbox_connector):
    """Test list files when not connected."""
    result = dropbox_connector.list_files()
    
    assert result == []


def test_list_files_success(dropbox_connector, mock_dropbox):
    """Test successful file listing."""
    mock_client = Mock()
    
    # Create mock file entries
    file1 = Mock()
    file1.path_display = '/TestRoot/file1.txt'
    file1.size = 100
    file1.client_modified = MagicMock()
    file1.content_hash = 'hash1'
    
    file2 = Mock()
    file2.path_display = '/TestRoot/file2.txt'
    file2.size = 200
    file2.client_modified = MagicMock()
    file2.content_hash = 'hash2'
    
    mock_result = Mock()
    mock_result.entries = [file1, file2]
    mock_result.has_more = False
    
    mock_client.files_list_folder.return_value = mock_result
    
    # Mock FileMetadata type
    mock_dropbox.files.FileMetadata = type(file1)
    
    dropbox_connector._connected = True
    dropbox_connector.dbx = mock_client
    
    result = dropbox_connector.list_files()
    
    assert len(result) == 2
    assert result[0]['path'] == '/TestRoot/file1.txt'
    assert result[0]['size'] == 100
    assert result[1]['path'] == '/TestRoot/file2.txt'


def test_get_file_metadata_not_connected(dropbox_connector):
    """Test get metadata when not connected."""
    result = dropbox_connector.get_file_metadata("test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_get_file_metadata_success(dropbox_connector, mock_dropbox):
    """Test successful metadata retrieval."""
    mock_client = Mock()
    mock_metadata = Mock()
    mock_metadata.size = 1024
    mock_metadata.client_modified = MagicMock()
    mock_metadata.content_hash = 'abc123'
    
    mock_client.files_get_metadata.return_value = mock_metadata
    
    # Mock FileMetadata type
    mock_dropbox.files.FileMetadata = type(mock_metadata)
    
    dropbox_connector._connected = True
    dropbox_connector.dbx = mock_client
    
    result = dropbox_connector.get_file_metadata("test.txt")
    
    assert result['success'] is True
    assert result['size'] == 1024
    assert result['checksum'] == 'abc123'


def test_get_full_path(dropbox_connector):
    """Test path combination logic."""
    # Test with relative path
    assert dropbox_connector._get_full_path('test.txt') == '/TestRoot/test.txt'
    
    # Test with absolute path
    assert dropbox_connector._get_full_path('/test.txt') == '/TestRoot/test.txt'
    
    # Test with empty root
    connector = DropboxConnector(access_token='token', root_path='')
    assert connector._get_full_path('test.txt') == '/test.txt'
