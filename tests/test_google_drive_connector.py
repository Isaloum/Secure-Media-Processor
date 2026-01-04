"""Test suite for Google Drive connector with fully mocked Google API calls."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
from datetime import datetime
import tempfile
import io
import sys


# Mock Google API modules before importing the connector
mock_service_account = MagicMock()
mock_service_account.Credentials = MagicMock()
mock_build = MagicMock()
mock_media = MagicMock()
mock_google_auth = MagicMock()

sys.modules['google'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.service_account'] = mock_service_account
sys.modules['google.auth'] = mock_google_auth
sys.modules['google.auth.exceptions'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = mock_build
sys.modules['googleapiclient.http'] = mock_media

from src.connectors.google_drive_connector import GoogleDriveConnector


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a test file for Google Drive upload.")
    return file_path


@pytest.fixture
def credentials_file(temp_dir):
    """Create a mock credentials JSON file."""
    cred_path = temp_dir / "credentials.json"
    cred_path.write_text('{"type": "service_account", "project_id": "test"}')
    return cred_path


@pytest.fixture
def connector(credentials_file):
    """Create a GoogleDriveConnector instance with mocked Google APIs."""
    return GoogleDriveConnector(
        credentials_path=credentials_file,
        folder_id='test_folder_id'
    )


class TestGoogleDriveConnectorInit:
    """Test initialization of GoogleDriveConnector."""
    
    def test_init_with_all_parameters(self, credentials_file):
        """Test connector initialization with all parameters."""
        connector = GoogleDriveConnector(
            credentials_path=credentials_file,
            folder_id='my_folder',
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        assert connector.credentials_path == credentials_file
        assert connector.folder_id == 'my_folder'
        assert connector.scopes == ['https://www.googleapis.com/auth/drive.file']
        assert connector.service is None
        assert connector.credentials is None
        assert not connector.is_connected()
    
    def test_init_with_defaults(self, credentials_file):
        """Test connector initialization with default parameters."""
        connector = GoogleDriveConnector(credentials_path=credentials_file)
        
        assert connector.folder_id is None
        assert connector.scopes == ['https://www.googleapis.com/auth/drive']
    
    def test_init_without_google_installed(self, credentials_file):
        """Test that ImportError is raised when Google APIs are not available."""
        with patch('src.connectors.google_drive_connector.GOOGLE_AVAILABLE', False):
            with pytest.raises(ImportError, match="Google Drive dependencies not installed"):
                GoogleDriveConnector(credentials_path=credentials_file)


class TestGoogleDriveConnectorConnection:
    """Test connection and disconnection."""
    
    def test_connect_success(self, connector, credentials_file):
        """Test successful connection to Google Drive."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        mock_service.about().get().execute.return_value = {'user': {'emailAddress': 'test@example.com'}}
        
        # Connect
        result = connector.connect()
        
        assert result is True
        assert connector.is_connected()
        assert connector.credentials == mock_creds
        assert connector.service == mock_service
        
        # Verify calls
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with(
            str(credentials_file),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_creds)
    
    def test_connect_missing_credentials_file(self):
        """Test connection failure when credentials file doesn't exist."""
        connector = GoogleDriveConnector(credentials_path='/nonexistent/creds.json')
        
        result = connector.connect()
        
        assert result is False
        assert not connector.is_connected()
    
    def test_connect_auth_error(self, connector, credentials_file):
        """Test connection failure due to authentication error."""
        # Setup mock to raise error
        mock_service_account.Credentials.from_service_account_file.side_effect = Exception("Auth failed")
        
        # Connect
        result = connector.connect()
        
        assert result is False
        assert not connector.is_connected()
    
    def test_disconnect(self, connector, credentials_file):
        """Test disconnection from Google Drive."""
        # First connect
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Then disconnect
        result = connector.disconnect()
        
        assert result is True
        assert not connector.is_connected()
        assert connector.service is None
        assert connector.credentials is None


class TestGoogleDriveConnectorUpload:
    """Test file upload operations."""
    
    def test_upload_file_success(self, connector, sample_file, credentials_file):
        """Test successful file upload."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock upload result
        mock_service.files().create().execute.return_value = {
            'id': 'file123',
            'name': 'remote_file.txt',
            'size': '100',
            'createdTime': '2024-01-01T12:00:00Z'
        }
        
        # Mock MediaFileUpload
        with patch('googleapiclient.http.MediaFileUpload') as mock_media:
            # Upload file
            result = connector.upload_file(sample_file, 'remote_file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == 'remote_file.txt'
        assert result['file_id'] == 'file123'
        assert 'checksum' in result
        assert 'timestamp' in result
        
        # Verify upload was called
        mock_service.files().create.assert_called_once()
        call_kwargs = mock_service.files().create.call_args[1]
        assert call_kwargs['body']['name'] == 'remote_file.txt'
        assert call_kwargs['body']['parents'] == ['test_folder_id']
    
    def test_upload_file_not_connected(self, connector, sample_file):
        """Test upload when not connected."""
        result = connector.upload_file(sample_file, 'remote_file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_upload_file_not_found(self, connector, temp_dir, credentials_file):
        """Test upload with non-existent file."""
        # Connect first
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Try to upload non-existent file
        non_existent = temp_dir / "nonexistent.txt"
        result = connector.upload_file(non_existent, 'remote_file.txt')
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_upload_file_with_metadata(self, connector, sample_file, credentials_file):
        """Test upload with custom metadata."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock upload result
        mock_service.files().create().execute.return_value = {
            'id': 'file123',
            'name': 'file.txt',
            'createdTime': '2024-01-01T12:00:00Z'
        }
        
        # Upload with metadata
        with patch('googleapiclient.http.MediaFileUpload'):
            metadata = {'user': 'test_user', 'purpose': 'testing'}
            result = connector.upload_file(sample_file, 'file.txt', metadata=metadata)
        
        assert result['success'] is True
        
        # Verify metadata was included
        call_kwargs = mock_service.files().create.call_args[1]
        assert 'user' in call_kwargs['body']['properties']
        assert call_kwargs['body']['properties']['user'] == 'test_user'
    
    def test_upload_file_without_folder(self, credentials_file, sample_file):
        """Test upload without specifying folder ID."""
        connector = GoogleDriveConnector(credentials_path=credentials_file)
        
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock upload result
        mock_service.files().create().execute.return_value = {
            'id': 'file123',
            'name': 'file.txt',
            'createdTime': '2024-01-01T12:00:00Z'
        }
        
        # Upload file
        with patch('googleapiclient.http.MediaFileUpload'):
            result = connector.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is True
        
        # Verify no parent folder was set
        call_kwargs = mock_service.files().create.call_args[1]
        assert 'parents' not in call_kwargs['body']
    
    def test_upload_file_api_error(self, connector, sample_file, credentials_file):
        """Test upload failure due to API error."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock API error
        with patch('googleapiclient.http.MediaFileUpload'):
            mock_service.files().create().execute.side_effect = Exception("Upload failed")
            
            # Upload file
            result = connector.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is False
        assert 'error' in result


class TestGoogleDriveConnectorDownload:
    """Test file download operations."""
    
    def test_download_file_success(self, connector, temp_dir, credentials_file):
        """Test successful file download."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock file search
        mock_service.files().get().execute.return_value = {'id': 'file123'}
        
        # Mock file metadata
        mock_service.files().get().execute.return_value = {
            'id': 'file123',
            'name': 'file.txt',
            'size': '18',
            'properties': {'checksum': 'test_checksum'}
        }
        
        # Mock download
        mock_request = MagicMock()
        mock_service.files().get_media.return_value = mock_request
        
        # Create a mock downloader
        with patch('googleapiclient.http.MediaIoBaseDownload') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
            mock_downloader_class.return_value = mock_downloader
            
            with patch('io.FileIO') as mock_fileio:
                mock_fh = MagicMock()
                mock_fileio.return_value = mock_fh
                
                # Actually write the file so it exists
                local_path = temp_dir / "downloaded.txt"
                local_path.write_text("Downloaded content")
                
                # Download file
                result = connector.download_file('file.txt', local_path, verify_checksum=False)
        
        assert result['success'] is True
        assert result['local_path'] == str(local_path)
    
    def test_download_file_not_connected(self, connector, temp_dir):
        """Test download when not connected."""
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('file.txt', local_path)
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_download_file_not_found(self, connector, temp_dir, credentials_file):
        """Test download when file doesn't exist."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id to return None
        with patch.object(connector, '_get_file_id', return_value=None):
            # Download file
            local_path = temp_dir / "downloaded.txt"
            result = connector.download_file('nonexistent.txt', local_path)
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_download_file_with_checksum_verification(self, connector, temp_dir, sample_file, credentials_file):
        """Test download with checksum verification."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Calculate real checksum
        checksum = connector._calculate_checksum(sample_file)
        
        # Mock file search
        mock_service.files().get().execute.return_value = {'id': 'file123'}
        
        # Mock file metadata with matching checksum
        mock_service.files().get().execute.return_value = {
            'id': 'file123',
            'name': 'file.txt',
            'size': str(sample_file.stat().st_size),
            'properties': {'checksum': checksum}
        }
        
        # Mock download
        mock_request = MagicMock()
        mock_service.files().get_media.return_value = mock_request
        
        with patch('googleapiclient.http.MediaIoBaseDownload') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
            mock_downloader_class.return_value = mock_downloader
            
            with patch('io.FileIO') as mock_fileio:
                # Write the actual file content
                local_path = temp_dir / "downloaded.txt"
                local_path.write_bytes(sample_file.read_bytes())
                
                # Download file
                result = connector.download_file('file.txt', local_path, verify_checksum=True)
        
        assert result['success'] is True
        assert result['checksum_verified'] is True
    
    def test_download_file_checksum_mismatch(self, connector, temp_dir, credentials_file):
        """Test download with checksum verification failure."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock file search
        mock_service.files().get().execute.return_value = {'id': 'file123'}
        
        # Mock file metadata with wrong checksum
        mock_service.files().get().execute.return_value = {
            'id': 'file123',
            'name': 'file.txt',
            'size': '18',
            'properties': {'checksum': 'wrong_checksum'}
        }
        
        # Mock download
        mock_request = MagicMock()
        mock_service.files().get_media.return_value = mock_request
        
        with patch('googleapiclient.http.MediaIoBaseDownload') as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
            mock_downloader_class.return_value = mock_downloader
            
            with patch('io.FileIO'):
                # Write file
                local_path = temp_dir / "downloaded.txt"
                local_path.write_text("Downloaded content")
                
                # Download file
                result = connector.download_file('file.txt', local_path, verify_checksum=True)
        
        # Should fail verification and delete the file
        assert result['success'] is False
        assert 'Checksum verification failed' in result['error']
        assert not local_path.exists()


class TestGoogleDriveConnectorDelete:
    """Test file deletion operations."""
    
    def test_delete_file_success(self, connector, credentials_file):
        """Test successful file deletion."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id to return file ID
        with patch.object(connector, '_get_file_id', return_value='file123'):
            # Delete file
            result = connector.delete_file('file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == 'file.txt'
        mock_service.files().delete().execute.assert_called_once()
    
    def test_delete_file_not_connected(self, connector):
        """Test deletion when not connected."""
        result = connector.delete_file('file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_delete_file_not_found(self, connector, credentials_file):
        """Test deletion when file doesn't exist."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id to return None
        with patch.object(connector, '_get_file_id', return_value=None):
            # Delete file
            result = connector.delete_file('nonexistent.txt')
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_delete_file_api_error(self, connector, credentials_file):
        """Test deletion failure due to API error."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id and deletion error
        with patch.object(connector, '_get_file_id', return_value='file123'):
            mock_service.files().delete().execute.side_effect = Exception("Delete failed")
            
            # Delete file
            result = connector.delete_file('file.txt')
        
        assert result['success'] is False
        assert 'error' in result


class TestGoogleDriveConnectorList:
    """Test file listing operations."""
    
    def test_list_files_success(self, connector, credentials_file):
        """Test successful file listing."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock list response
        mock_service.files().list().execute.return_value = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'file1.txt',
                    'size': '100',
                    'modifiedTime': '2024-01-01T12:00:00Z',
                    'md5Checksum': 'abc123'
                },
                {
                    'id': 'file2',
                    'name': 'file2.txt',
                    'size': '200',
                    'modifiedTime': '2024-01-02T12:00:00Z',
                    'md5Checksum': 'def456'
                }
            ]
        }
        
        # List files
        files = connector.list_files()
        
        assert len(files) == 2
        assert files[0]['path'] == 'file1.txt'
        assert files[0]['file_id'] == 'file1'
        assert files[0]['size'] == 100
        assert files[0]['checksum'] == 'abc123'
        assert files[1]['path'] == 'file2.txt'
    
    def test_list_files_with_prefix(self, connector, credentials_file):
        """Test listing with name prefix filter."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock empty response
        mock_service.files().list().execute.return_value = {'files': []}
        
        # List files with prefix
        files = connector.list_files(prefix='test')
        
        # Verify query includes prefix
        call_kwargs = mock_service.files().list.call_args[1]
        assert 'test' in call_kwargs['q']
        assert 'name contains' in call_kwargs['q']
    
    def test_list_files_not_connected(self, connector):
        """Test listing when not connected."""
        files = connector.list_files()
        
        assert files == []
    
    def test_list_files_api_error(self, connector, credentials_file):
        """Test listing failure due to API error."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock API error
        mock_service.files().list().execute.side_effect = Exception("List failed")
        
        # List files
        files = connector.list_files()
        
        assert files == []


class TestGoogleDriveConnectorMetadata:
    """Test file metadata operations."""
    
    def test_get_file_metadata_success(self, connector, credentials_file):
        """Test successful metadata retrieval."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id and metadata
        with patch.object(connector, '_get_file_id', return_value='file123'):
            mock_service.files().get().execute.return_value = {
                'id': 'file123',
                'name': 'file.txt',
                'size': '1024',
                'modifiedTime': '2024-01-01T12:00:00Z',
                'properties': {'user': 'test_user'},
                'md5Checksum': 'abc123'
            }
            
            # Get metadata
            result = connector.get_file_metadata('file.txt')
        
        assert result['success'] is True
        assert result['size'] == 1024
        assert result['metadata']['user'] == 'test_user'
        assert result['checksum'] == 'abc123'
    
    def test_get_file_metadata_not_connected(self, connector):
        """Test metadata retrieval when not connected."""
        result = connector.get_file_metadata('file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_get_file_metadata_not_found(self, connector, credentials_file):
        """Test metadata for non-existent file."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock _get_file_id to return None
        with patch.object(connector, '_get_file_id', return_value=None):
            # Get metadata
            result = connector.get_file_metadata('nonexistent.txt')
        
        assert result['success'] is False
        assert 'File not found' in result['error']


class TestGoogleDriveConnectorHelpers:
    """Test helper methods."""
    
    def test_get_file_id_by_id(self, connector, credentials_file):
        """Test getting file ID when input is already an ID."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock successful get by ID
        mock_service.files().get().execute.return_value = {'id': 'file123'}
        
        # Get file ID
        file_id = connector._get_file_id('file123')
        
        assert file_id == 'file123'
    
    def test_get_file_id_by_name(self, connector, credentials_file):
        """Test getting file ID by name search."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock failed get by ID, successful search by name
        mock_service.files().get().execute.side_effect = Exception("Not an ID")
        mock_service.files().list().execute.return_value = {
            'files': [{'id': 'found123'}]
        }
        
        # Get file ID
        file_id = connector._get_file_id('myfile.txt')
        
        assert file_id == 'found123'
    
    def test_get_file_id_not_found(self, connector, credentials_file):
        """Test getting file ID when file doesn't exist."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock failed get by ID and empty search results
        mock_service.files().get().execute.side_effect = Exception("Not an ID")
        mock_service.files().list().execute.return_value = {'files': []}
        
        # Get file ID
        file_id = connector._get_file_id('nonexistent.txt')
        
        assert file_id is None
    
    def test_get_file_id_with_folder(self, connector, credentials_file):
        """Test file ID search includes folder filter."""
        # Setup mocks
        mock_creds = MagicMock()
        mock_service = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds
        mock_build.return_value = mock_service
        connector.connect()
        
        # Mock failed get by ID, successful search with folder
        mock_service.files().get().execute.side_effect = Exception("Not an ID")
        mock_service.files().list().execute.return_value = {
            'files': [{'id': 'found123'}]
        }
        
        # Get file ID
        file_id = connector._get_file_id('myfile.txt')
        
        # Verify query includes folder
        call_kwargs = mock_service.files().list.call_args[1]
        assert 'test_folder_id' in call_kwargs['q']
        assert 'in parents' in call_kwargs['q']
