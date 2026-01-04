"""Test suite for Dropbox connector with fully mocked API calls."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import tempfile
import sys


# Create actual mock classes for isinstance checks
class MockFileMetadata:
    """Mock FileMetadata class."""
    pass


class MockFolderMetadata:
    """Mock FolderMetadata class."""
    pass


# Mock dropbox module before importing the connector
mock_dropbox = MagicMock()
mock_dropbox.files = MagicMock()
mock_dropbox.files.WriteMode = MagicMock(return_value='overwrite')
mock_dropbox.files.FileMetadata = MockFileMetadata
mock_dropbox.files.FolderMetadata = MockFolderMetadata
mock_dropbox.exceptions = MagicMock()
mock_dropbox.exceptions.AuthError = Exception
mock_dropbox.exceptions.ApiError = Exception

sys.modules['dropbox'] = mock_dropbox
sys.modules['dropbox.files'] = mock_dropbox.files
sys.modules['dropbox.exceptions'] = mock_dropbox.exceptions

from src.connectors.dropbox_connector import DropboxConnector


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a test file for Dropbox upload.")
    return file_path


@pytest.fixture
def connector():
    """Create a DropboxConnector instance with mocked Dropbox."""
    return DropboxConnector(access_token='test_token', root_path='/test')


class TestDropboxConnectorInit:
    """Test initialization of DropboxConnector."""
    
    def test_init_with_defaults(self):
        """Test connector initialization with default parameters."""
        connector = DropboxConnector(access_token='test_token')
        
        assert connector.access_token == 'test_token'
        assert connector.root_path == ''
        assert connector.dbx is None
        assert not connector.is_connected()
    
    def test_init_with_root_path(self):
        """Test connector initialization with root path."""
        connector = DropboxConnector(access_token='test_token', root_path='/SecureMedia/')
        
        assert connector.root_path == '/SecureMedia'
    
    def test_init_without_dropbox_installed(self):
        """Test that ImportError is raised when Dropbox SDK is not available."""
        with patch('src.connectors.dropbox_connector.DROPBOX_AVAILABLE', False):
            with pytest.raises(ImportError, match="Dropbox SDK not installed"):
                DropboxConnector(access_token='test_token')


class TestDropboxConnectorConnection:
    """Test connection and disconnection."""
    
    def test_connect_success(self, connector):
        """Test successful connection to Dropbox."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.users_get_current_account.return_value = {'account_id': 'test123'}
        mock_dropbox.Dropbox.return_value = mock_client
        
        # Connect
        result = connector.connect()
        
        assert result is True
        assert connector.is_connected()
        assert connector.dbx == mock_client
        mock_dropbox.Dropbox.assert_called_once_with('test_token')
        mock_client.users_get_current_account.assert_called_once()
    
    def test_connect_auth_error(self, connector):
        """Test connection failure due to authentication error."""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_client.users_get_current_account.side_effect = Exception("Auth failed")
        mock_dropbox.Dropbox.return_value = mock_client
        
        # Connect
        result = connector.connect()
        
        assert result is False
        assert not connector.is_connected()
    
    def test_disconnect(self, connector):
        """Test disconnection from Dropbox."""
        # First connect
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Then disconnect
        result = connector.disconnect()
        
        assert result is True
        assert not connector.is_connected()
        assert connector.dbx is None


class TestDropboxConnectorUpload:
    """Test file upload operations."""
    
    def test_upload_file_success(self, connector, sample_file):
        """Test successful file upload."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock upload result
        mock_upload_result = MagicMock()
        mock_upload_result.path_display = '/test/remote/file.txt'
        mock_upload_result.size = 38
        mock_upload_result.client_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_client.files_upload.return_value = mock_upload_result
        
        # Upload file
        result = connector.upload_file(sample_file, 'remote/file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == '/test/remote/file.txt'
        assert result['size'] == 38
        assert 'checksum' in result
        assert 'timestamp' in result
        
        # Verify the upload was called with correct parameters
        mock_client.files_upload.assert_called_once()
        call_args = mock_client.files_upload.call_args
        assert call_args[0][1] == '/test/remote/file.txt'
    
    def test_upload_file_not_connected(self, connector, sample_file):
        """Test upload when not connected."""
        result = connector.upload_file(sample_file, 'remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_upload_file_not_found(self, connector, temp_dir):
        """Test upload with non-existent file."""
        # Connect first
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Try to upload non-existent file
        non_existent = temp_dir / "nonexistent.txt"
        result = connector.upload_file(non_existent, 'remote/file.txt')
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_upload_file_with_metadata(self, connector, sample_file):
        """Test upload with custom metadata."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock upload result
        mock_upload_result = MagicMock()
        mock_upload_result.path_display = '/test/file.txt'
        mock_upload_result.size = 38
        mock_upload_result.client_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_client.files_upload.return_value = mock_upload_result
        
        # Upload with metadata
        metadata = {'user': 'test_user', 'purpose': 'testing'}
        result = connector.upload_file(sample_file, 'file.txt', metadata=metadata)
        
        assert result['success'] is True
    
    def test_upload_file_api_error(self, connector, sample_file):
        """Test upload failure due to API error."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock API error
        mock_client.files_upload.side_effect = Exception("API Error")
        
        # Upload file
        result = connector.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is False
        assert 'error' in result


class TestDropboxConnectorDownload:
    """Test file download operations."""
    
    def test_download_file_success(self, connector, temp_dir):
        """Test successful file download."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock download response
        mock_metadata = MagicMock()
        mock_metadata.content_hash = 'test_hash'
        mock_response = MagicMock()
        mock_response.content = b'Downloaded content'
        mock_client.files_download.return_value = (mock_metadata, mock_response)
        
        # Download file
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path)
        
        assert result['success'] is True
        assert result['local_path'] == str(local_path)
        assert local_path.exists()
        assert local_path.read_bytes() == b'Downloaded content'
        
        # Verify the download was called with correct path
        mock_client.files_download.assert_called_once_with('/test/remote/file.txt')
    
    def test_download_file_not_connected(self, connector, temp_dir):
        """Test download when not connected."""
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path)
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_download_file_api_error(self, connector, temp_dir):
        """Test download failure due to API error."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock API error
        mock_client.files_download.side_effect = Exception("File not found")
        
        # Download file
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path)
        
        assert result['success'] is False
        assert 'error' in result


class TestDropboxConnectorDelete:
    """Test file deletion operations."""
    
    def test_delete_file_success(self, connector):
        """Test successful file deletion."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock delete response
        mock_client.files_delete_v2.return_value = MagicMock()
        
        # Delete file
        result = connector.delete_file('remote/file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == '/test/remote/file.txt'
        mock_client.files_delete_v2.assert_called_once_with('/test/remote/file.txt')
    
    def test_delete_file_not_connected(self, connector):
        """Test deletion when not connected."""
        result = connector.delete_file('remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_delete_file_api_error(self, connector):
        """Test deletion failure due to API error."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock API error
        mock_client.files_delete_v2.side_effect = Exception("File not found")
        
        # Delete file
        result = connector.delete_file('remote/file.txt')
        
        assert result['success'] is False
        assert 'error' in result


class TestDropboxConnectorList:
    """Test file listing operations."""
    
    def test_list_files_success(self, connector):
        """Test successful file listing."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Create mock file entries - instantiate the actual mock class
        mock_file1 = MockFileMetadata()
        mock_file1.path_display = '/test/file1.txt'
        mock_file1.size = 100
        mock_file1.client_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_file1.content_hash = 'hash1'
        
        mock_file2 = MockFileMetadata()
        mock_file2.path_display = '/test/file2.txt'
        mock_file2.size = 200
        mock_file2.client_modified = datetime(2024, 1, 2, 12, 0, 0)
        mock_file2.content_hash = 'hash2'
        
        # Mock list result
        mock_result = MagicMock()
        mock_result.entries = [mock_file1, mock_file2]
        mock_result.has_more = False
        mock_client.files_list_folder.return_value = mock_result
        
        # List files
        files = connector.list_files()
        
        assert len(files) == 2
        assert files[0]['path'] == '/test/file1.txt'
        assert files[0]['size'] == 100
        assert files[1]['path'] == '/test/file2.txt'
        assert files[1]['size'] == 200
    
    def test_list_files_not_connected(self, connector):
        """Test listing when not connected."""
        files = connector.list_files()
        
        assert files == []
    
    def test_list_files_with_prefix(self, connector):
        """Test listing with path prefix."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock empty result
        mock_result = MagicMock()
        mock_result.entries = []
        mock_result.has_more = False
        mock_client.files_list_folder.return_value = mock_result
        
        # List files with prefix
        files = connector.list_files(prefix='subfolder')
        
        mock_client.files_list_folder.assert_called_once_with('/test/subfolder', recursive=True)
    
    def test_list_files_pagination(self, connector):
        """Test listing with pagination."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Create mock file
        mock_file = MockFileMetadata()
        mock_file.path_display = '/test/file.txt'
        mock_file.size = 100
        mock_file.client_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_file.content_hash = 'hash1'
        
        # First page has more results
        mock_result1 = MagicMock()
        mock_result1.entries = [mock_file]
        mock_result1.has_more = True
        mock_result1.cursor = 'cursor123'
        
        # Second page is last
        mock_result2 = MagicMock()
        mock_result2.entries = [mock_file]
        mock_result2.has_more = False
        
        mock_client.files_list_folder.return_value = mock_result1
        mock_client.files_list_folder_continue.return_value = mock_result2
        
        # List files
        files = connector.list_files()
        
        assert len(files) == 2
        mock_client.files_list_folder_continue.assert_called_once_with('cursor123')


class TestDropboxConnectorMetadata:
    """Test file metadata operations."""
    
    def test_get_file_metadata_success(self, connector):
        """Test successful metadata retrieval."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock metadata - instantiate the actual mock class
        mock_metadata = MockFileMetadata()
        mock_metadata.size = 1024
        mock_metadata.client_modified = datetime(2024, 1, 1, 12, 0, 0)
        mock_metadata.content_hash = 'test_hash'
        mock_client.files_get_metadata.return_value = mock_metadata
        
        # Get metadata
        result = connector.get_file_metadata('remote/file.txt')
        
        assert result['success'] is True
        assert result['size'] == 1024
        assert 'checksum' in result
        mock_client.files_get_metadata.assert_called_once_with('/test/remote/file.txt')
    
    def test_get_file_metadata_not_connected(self, connector):
        """Test metadata retrieval when not connected."""
        result = connector.get_file_metadata('remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_get_file_metadata_not_a_file(self, connector):
        """Test metadata for a non-file (e.g., folder)."""
        # Setup mock
        mock_client = MagicMock()
        mock_dropbox.Dropbox.return_value = mock_client
        connector.connect()
        
        # Mock folder metadata - use FolderMetadata instead of FileMetadata
        mock_metadata = MockFolderMetadata()
        mock_client.files_get_metadata.return_value = mock_metadata
        
        # Get metadata
        result = connector.get_file_metadata('remote/folder')
        
        assert result['success'] is False
        assert 'not a file' in result['error']


class TestDropboxConnectorHelpers:
    """Test helper methods."""
    
    def test_get_full_path_with_root(self, connector):
        """Test path construction with root path."""
        full_path = connector._get_full_path('file.txt')
        assert full_path == '/test/file.txt'
        
        full_path = connector._get_full_path('/file.txt')
        assert full_path == '/test/file.txt'
    
    def test_get_full_path_without_root(self):
        """Test path construction without root path."""
        connector = DropboxConnector(access_token='test_token', root_path='')
        
        full_path = connector._get_full_path('file.txt')
        assert full_path == '/file.txt'
        
        full_path = connector._get_full_path('/file.txt')
        assert full_path == '/file.txt'
