"""Test suite for Google Drive connector."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# Mock the Google modules at import time
sys.modules['google'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.service_account'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.exceptions'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()

from src.connectors.google_drive_connector import GoogleDriveConnector


@pytest.fixture
def mock_google_apis():
    """Create mock Google APIs."""
    # The modules are already mocked at import time
    return sys.modules['google.oauth2.service_account'], sys.modules['googleapiclient.discovery']


@pytest.fixture
def google_drive_connector(tmp_path):
    """Create Google Drive connector instance."""
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{"type": "service_account"}')
    
    return GoogleDriveConnector(
        credentials_path=creds_file,
        folder_id='test-folder-id'
    )


def test_google_drive_connector_initialization(tmp_path):
    """Test Google Drive connector initialization."""
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{}')
    
    connector = GoogleDriveConnector(
        credentials_path=creds_file,
        folder_id='my-folder-id'
    )
    
    assert connector.credentials_path == creds_file
    assert connector.folder_id == 'my-folder-id'
    assert not connector.is_connected()


def test_connect_success(google_drive_connector, mock_google_apis):
    """Test successful connection to Google Drive."""
    mock_sa, mock_build = mock_google_apis
    mock_creds = Mock()
    mock_sa.Credentials.from_service_account_file.return_value = mock_creds
    
    mock_service = Mock()
    mock_build.return_value = mock_service
    
    result = google_drive_connector.connect()
    
    assert result is True
    assert google_drive_connector.is_connected()
    mock_service.about().get.assert_called_once()


def test_connect_failure_no_credentials(google_drive_connector, mock_google_apis):
    """Test failed connection with missing credentials."""
    google_drive_connector.credentials_path = Path("/nonexistent/creds.json")
    
    result = google_drive_connector.connect()
    
    assert result is False
    assert not google_drive_connector.is_connected()


def test_disconnect(google_drive_connector):
    """Test disconnection from Google Drive."""
    google_drive_connector._connected = True
    google_drive_connector.service = Mock()
    
    result = google_drive_connector.disconnect()
    
    assert result is True
    assert not google_drive_connector.is_connected()
    assert google_drive_connector.service is None


def test_upload_file_not_connected(google_drive_connector, tmp_path):
    """Test upload when not connected."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = google_drive_connector.upload_file(test_file, "test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_upload_file_not_found(google_drive_connector, mock_google_apis):
    """Test upload with non-existent file."""
    google_drive_connector._connected = True
    google_drive_connector.service = Mock()
    
    result = google_drive_connector.upload_file("/nonexistent/file.txt", "test.txt")
    
    assert result['success'] is False
    assert 'File not found' in result['error']


def test_upload_file_success(google_drive_connector, tmp_path, mock_google_apis):
    """Test successful file upload."""
    mock_service = Mock()
    mock_files = Mock()
    mock_create = Mock()
    mock_create.execute.return_value = {
        'id': 'file-id-123',
        'name': 'test.txt',
        'size': 12,
        'createdTime': '2024-01-01T00:00:00Z'
    }
    mock_files.create.return_value = mock_create
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    with patch('googleapiclient.http.MediaFileUpload'):
        result = google_drive_connector.upload_file(test_file, "test.txt")
    
    assert result['success'] is True
    assert result['remote_path'] == 'test.txt'
    assert result['file_id'] == 'file-id-123'
    assert 'checksum' in result


def test_download_file_not_connected(google_drive_connector, tmp_path):
    """Test download when not connected."""
    local_path = tmp_path / "downloaded.txt"
    
    result = google_drive_connector.download_file("test.txt", local_path)
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_download_file_success(google_drive_connector, tmp_path, mock_google_apis):
    """Test successful file download."""
    mock_service = Mock()
    mock_files = Mock()
    
    # Mock get file ID
    mock_get = Mock()
    mock_get.execute.return_value = {'id': 'file-id-123'}
    mock_files.get.return_value = mock_get
    
    # Mock get metadata
    mock_get_metadata = Mock()
    mock_get_metadata.execute.return_value = {
        'id': 'file-id-123',
        'name': 'test.txt',
        'size': 12,
        'properties': {'checksum': 'abc123'}
    }
    
    # Mock get_media
    mock_get_media = Mock()
    
    mock_files.get.side_effect = [mock_get, mock_get_metadata, mock_get_media]
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    local_path = tmp_path / "downloaded.txt"
    
    with patch('googleapiclient.http.MediaIoBaseDownload') as mock_download, \
         patch('io.FileIO') as mock_fh:
        
        # Mock the download process
        mock_downloader = Mock()
        mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
        mock_download.return_value = mock_downloader
        
        # Create the file for testing
        local_path.write_text("test content")
        
        with patch.object(google_drive_connector, '_calculate_checksum', return_value='abc123'):
            result = google_drive_connector.download_file("test.txt", local_path)
    
    assert result['success'] is True
    assert result['checksum_verified'] is True


def test_download_file_checksum_mismatch(google_drive_connector, tmp_path, mock_google_apis):
    """Test download with checksum verification failure."""
    mock_service = Mock()
    mock_files = Mock()
    
    mock_get = Mock()
    mock_get.execute.return_value = {'id': 'file-id-123'}
    mock_files.get.return_value = mock_get
    
    mock_get_metadata = Mock()
    mock_get_metadata.execute.return_value = {
        'id': 'file-id-123',
        'name': 'test.txt',
        'size': 12,
        'properties': {'checksum': 'expected_checksum'}
    }
    
    mock_get_media = Mock()
    mock_files.get.side_effect = [mock_get, mock_get_metadata, mock_get_media]
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    local_path = tmp_path / "downloaded.txt"
    
    with patch('googleapiclient.http.MediaIoBaseDownload') as mock_download, \
         patch('io.FileIO') as mock_fh:
        
        mock_downloader = Mock()
        mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
        mock_download.return_value = mock_downloader
        
        local_path.write_text("test content")
        
        with patch.object(google_drive_connector, '_calculate_checksum', return_value='wrong_checksum'):
            result = google_drive_connector.download_file("test.txt", local_path, verify_checksum=True)
    
    assert result['success'] is False
    assert 'Checksum verification failed' in result['error']
    assert not local_path.exists()


def test_delete_file_not_connected(google_drive_connector):
    """Test delete when not connected."""
    result = google_drive_connector.delete_file("test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_delete_file_success(google_drive_connector, mock_google_apis):
    """Test successful file deletion."""
    mock_service = Mock()
    mock_files = Mock()
    
    mock_get = Mock()
    mock_get.execute.return_value = {'id': 'file-id-123'}
    mock_files.get.return_value = mock_get
    
    mock_delete = Mock()
    mock_delete.execute.return_value = {}
    mock_files.delete.return_value = mock_delete
    
    mock_files.get.side_effect = [mock_get]
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    result = google_drive_connector.delete_file("test.txt")
    
    assert result['success'] is True
    mock_delete.execute.assert_called_once()


def test_list_files_not_connected(google_drive_connector):
    """Test list files when not connected."""
    result = google_drive_connector.list_files()
    
    assert result == []


def test_list_files_success(google_drive_connector, mock_google_apis):
    """Test successful file listing."""
    mock_service = Mock()
    mock_files = Mock()
    
    mock_list = Mock()
    mock_list.execute.return_value = {
        'files': [
            {
                'id': 'file1',
                'name': 'file1.txt',
                'size': '100',
                'modifiedTime': '2024-01-01T00:00:00Z',
                'md5Checksum': 'hash1'
            },
            {
                'id': 'file2',
                'name': 'file2.txt',
                'size': '200',
                'modifiedTime': '2024-01-02T00:00:00Z',
                'md5Checksum': 'hash2'
            }
        ]
    }
    mock_files.list.return_value = mock_list
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    result = google_drive_connector.list_files()
    
    assert len(result) == 2
    assert result[0]['path'] == 'file1.txt'
    assert result[0]['size'] == 100
    assert result[1]['path'] == 'file2.txt'


def test_get_file_metadata_not_connected(google_drive_connector):
    """Test get metadata when not connected."""
    result = google_drive_connector.get_file_metadata("test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_get_file_metadata_success(google_drive_connector, mock_google_apis):
    """Test successful metadata retrieval."""
    mock_service = Mock()
    mock_files = Mock()
    
    mock_get_id = Mock()
    mock_get_id.execute.return_value = {'id': 'file-id-123'}
    
    mock_get_metadata = Mock()
    mock_get_metadata.execute.return_value = {
        'id': 'file-id-123',
        'name': 'test.txt',
        'size': '1024',
        'modifiedTime': '2024-01-01T00:00:00Z',
        'properties': {'custom': 'value'},
        'md5Checksum': 'abc123'
    }
    
    mock_files.get.side_effect = [mock_get_id, mock_get_metadata]
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    result = google_drive_connector.get_file_metadata("test.txt")
    
    assert result['success'] is True
    assert result['size'] == 1024
    assert result['metadata'] == {'custom': 'value'}
    assert result['checksum'] == 'abc123'


def test_get_file_id_by_id(google_drive_connector, mock_google_apis):
    """Test getting file ID when already an ID."""
    mock_service = Mock()
    mock_files = Mock()
    
    mock_get = Mock()
    mock_get.execute.return_value = {'id': 'file-id-123'}
    mock_files.get.return_value = mock_get
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    result = google_drive_connector._get_file_id('file-id-123')
    
    assert result == 'file-id-123'


def test_get_file_id_by_name(google_drive_connector, mock_google_apis):
    """Test getting file ID by name."""
    mock_service = Mock()
    mock_files = Mock()
    
    # First call fails (not an ID)
    mock_get = Mock()
    mock_get.execute.side_effect = Exception("Not found")
    
    # Second call succeeds (search by name)
    mock_list = Mock()
    mock_list.execute.return_value = {
        'files': [{'id': 'found-file-id'}]
    }
    
    mock_files.get.return_value = mock_get
    mock_files.list.return_value = mock_list
    mock_service.files.return_value = mock_files
    
    google_drive_connector._connected = True
    google_drive_connector.service = mock_service
    
    result = google_drive_connector._get_file_id('test.txt')
    
    assert result == 'found-file-id'
