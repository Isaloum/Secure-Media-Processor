"""Test suite for S3 connector with fully mocked boto3 calls."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import tempfile

from src.connectors.s3_connector import S3Connector


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a test file for S3 upload.")
    return file_path


@pytest.fixture
def mock_boto3():
    """Mock the boto3 module."""
    with patch('src.connectors.s3_connector.boto3') as mock_boto:
        yield mock_boto


@pytest.fixture
def connector(mock_boto3):
    """Create an S3Connector instance with mocked boto3."""
    return S3Connector(
        bucket_name='test-bucket',
        region='us-east-1',
        access_key='test_key',
        secret_key='test_secret'
    )


class TestS3ConnectorInit:
    """Test initialization of S3Connector."""
    
    def test_init_with_all_parameters(self, mock_boto3):
        """Test connector initialization with all parameters."""
        connector = S3Connector(
            bucket_name='my-bucket',
            region='us-west-2',
            access_key='my_key',
            secret_key='my_secret',
            encryption='aws:kms'
        )
        
        assert connector.bucket_name == 'my-bucket'
        assert connector.region == 'us-west-2'
        assert connector.access_key == 'my_key'
        assert connector.secret_key == 'my_secret'
        assert connector.encryption == 'aws:kms'
        assert connector.s3_client is None
        assert connector.s3_resource is None
        assert not connector.is_connected()
    
    def test_init_with_defaults(self, mock_boto3):
        """Test connector initialization with default parameters."""
        connector = S3Connector(bucket_name='test-bucket')
        
        assert connector.bucket_name == 'test-bucket'
        assert connector.region == 'us-east-1'
        assert connector.encryption == 'AES256'
        assert connector.access_key is None
        assert connector.secret_key is None


class TestS3ConnectorConnection:
    """Test connection and disconnection."""
    
    def test_connect_success_with_credentials(self, connector, mock_boto3):
        """Test successful connection to S3 with credentials."""
        # Setup mocks
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        
        # Connect
        result = connector.connect()
        
        assert result is True
        assert connector.is_connected()
        assert connector.s3_client == mock_client
        assert connector.s3_resource == mock_resource
        
        # Verify boto3 was called with correct parameters
        mock_boto3.client.assert_called_once_with(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret'
        )
        mock_boto3.resource.assert_called_once_with(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret'
        )
        mock_client.head_bucket.assert_called_once_with(Bucket='test-bucket')
    
    def test_connect_success_without_credentials(self, mock_boto3):
        """Test successful connection using environment credentials."""
        connector = S3Connector(bucket_name='test-bucket')
        
        # Setup mocks
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        
        # Connect
        result = connector.connect()
        
        assert result is True
        assert connector.is_connected()
        
        # Verify boto3 was called without credentials
        mock_boto3.client.assert_called_once_with('s3', region_name='us-east-1')
        mock_boto3.resource.assert_called_once_with('s3', region_name='us-east-1')
    
    def test_connect_client_error(self, connector, mock_boto3):
        """Test connection failure due to client error."""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.head_bucket.side_effect = Exception("Bucket not found")
            
            # Connect
            result = connector.connect()
            
            assert result is False
            assert not connector.is_connected()
    
    def test_connect_no_credentials_error(self, connector, mock_boto3):
        """Test connection failure due to missing credentials."""
        with patch('src.connectors.s3_connector.NoCredentialsError', Exception):
            mock_boto3.client.side_effect = Exception("No credentials")
            
            # Connect
            result = connector.connect()
            
            assert result is False
            assert not connector.is_connected()
    
    def test_disconnect(self, connector, mock_boto3):
        """Test disconnection from S3."""
        # First connect
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Then disconnect
        result = connector.disconnect()
        
        assert result is True
        assert not connector.is_connected()
        assert connector.s3_client is None
        assert connector.s3_resource is None


class TestS3ConnectorUpload:
    """Test file upload operations."""
    
    def test_upload_file_success(self, connector, sample_file, mock_boto3):
        """Test successful file upload."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Upload file
        result = connector.upload_file(sample_file, 'remote/file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == 'remote/file.txt'
        assert result['size'] == sample_file.stat().st_size
        assert 'checksum' in result
        assert 'timestamp' in result
        
        # Verify upload was called
        mock_client.upload_file.assert_called_once()
        call_args = mock_client.upload_file.call_args
        assert call_args[0][0] == str(sample_file)
        assert call_args[0][1] == 'test-bucket'
        assert call_args[0][2] == 'remote/file.txt'
        
        # Verify encryption settings
        extra_args = call_args[1]['ExtraArgs']
        assert extra_args['ServerSideEncryption'] == 'AES256'
        assert 'checksum' in extra_args['Metadata']
    
    def test_upload_file_not_connected(self, connector, sample_file):
        """Test upload when not connected."""
        result = connector.upload_file(sample_file, 'remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_upload_file_not_found(self, connector, temp_dir, mock_boto3):
        """Test upload with non-existent file."""
        # Connect first
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Try to upload non-existent file
        non_existent = temp_dir / "nonexistent.txt"
        result = connector.upload_file(non_existent, 'remote/file.txt')
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_upload_file_with_metadata(self, connector, sample_file, mock_boto3):
        """Test upload with custom metadata."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Upload with metadata
        metadata = {'user': 'test_user', 'purpose': 'testing'}
        result = connector.upload_file(sample_file, 'file.txt', metadata=metadata)
        
        assert result['success'] is True
        
        # Verify metadata was included
        call_args = mock_client.upload_file.call_args
        extra_args = call_args[1]['ExtraArgs']
        assert extra_args['Metadata']['user'] == 'test_user'
        assert extra_args['Metadata']['purpose'] == 'testing'
    
    def test_upload_file_with_kms_encryption(self, mock_boto3, sample_file):
        """Test upload with KMS encryption."""
        connector = S3Connector(
            bucket_name='test-bucket',
            encryption='aws:kms'
        )
        
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Upload file
        result = connector.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is True
        
        # Verify KMS encryption
        call_args = mock_client.upload_file.call_args
        assert call_args[1]['ExtraArgs']['ServerSideEncryption'] == 'aws:kms'
    
    def test_upload_file_client_error(self, connector, sample_file, mock_boto3):
        """Test upload failure due to client error."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock client error
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.upload_file.side_effect = Exception("Upload failed")
            
            # Upload file
            result = connector.upload_file(sample_file, 'file.txt')
            
            assert result['success'] is False
            assert 'error' in result


class TestS3ConnectorDownload:
    """Test file download operations."""
    
    def test_download_file_success(self, connector, temp_dir, mock_boto3):
        """Test successful file download."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock head_object response
        mock_client.head_object.return_value = {
            'Metadata': {'checksum': 'test_checksum'},
            'ContentLength': 100
        }
        
        # Mock download
        def mock_download(bucket, key, path):
            Path(path).write_text("Downloaded content")
        
        mock_client.download_file.side_effect = mock_download
        
        # Download file
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path, verify_checksum=False)
        
        assert result['success'] is True
        assert result['local_path'] == str(local_path)
        assert local_path.exists()
        
        # Verify calls
        mock_client.head_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='remote/file.txt'
        )
        mock_client.download_file.assert_called_once_with(
            'test-bucket',
            'remote/file.txt',
            str(local_path)
        )
    
    def test_download_file_with_checksum_verification(self, connector, temp_dir, sample_file, mock_boto3):
        """Test download with checksum verification."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Calculate real checksum
        checksum = connector._calculate_checksum(sample_file)
        
        # Mock head_object response with matching checksum
        mock_client.head_object.return_value = {
            'Metadata': {'checksum': checksum},
            'ContentLength': sample_file.stat().st_size
        }
        
        # Mock download - copy the actual file content
        def mock_download(bucket, key, path):
            Path(path).write_bytes(sample_file.read_bytes())
        
        mock_client.download_file.side_effect = mock_download
        
        # Download file with verification
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path, verify_checksum=True)
        
        assert result['success'] is True
        assert result['checksum_verified'] is True
    
    def test_download_file_checksum_mismatch(self, connector, temp_dir, mock_boto3):
        """Test download with checksum verification failure."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock head_object with wrong checksum
        mock_client.head_object.return_value = {
            'Metadata': {'checksum': 'wrong_checksum'},
            'ContentLength': 100
        }
        
        # Mock download
        def mock_download(bucket, key, path):
            Path(path).write_text("Downloaded content")
        
        mock_client.download_file.side_effect = mock_download
        
        # Download file
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path, verify_checksum=True)
        
        # Should fail verification and delete the file
        assert result['success'] is False
        assert 'Checksum verification failed' in result['error']
        assert not local_path.exists()
    
    def test_download_file_not_connected(self, connector, temp_dir):
        """Test download when not connected."""
        local_path = temp_dir / "downloaded.txt"
        result = connector.download_file('remote/file.txt', local_path)
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_download_file_client_error(self, connector, temp_dir, mock_boto3):
        """Test download failure due to client error."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock client error
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.head_object.side_effect = Exception("Not found")
            
            # Download file
            local_path = temp_dir / "downloaded.txt"
            result = connector.download_file('remote/file.txt', local_path)
            
            assert result['success'] is False
            assert 'error' in result


class TestS3ConnectorDelete:
    """Test file deletion operations."""
    
    def test_delete_file_success(self, connector, mock_boto3):
        """Test successful file deletion."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Delete file
        result = connector.delete_file('remote/file.txt')
        
        assert result['success'] is True
        assert result['remote_path'] == 'remote/file.txt'
        
        mock_client.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='remote/file.txt'
        )
    
    def test_delete_file_not_connected(self, connector):
        """Test deletion when not connected."""
        result = connector.delete_file('remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_delete_file_client_error(self, connector, mock_boto3):
        """Test deletion failure due to client error."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock client error
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.delete_object.side_effect = Exception("Delete failed")
            
            # Delete file
            result = connector.delete_file('remote/file.txt')
            
            assert result['success'] is False
            assert 'error' in result


class TestS3ConnectorList:
    """Test file listing operations."""
    
    def test_list_files_success(self, connector, mock_boto3):
        """Test successful file listing."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock list response
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'file1.txt',
                    'Size': 100,
                    'LastModified': datetime(2024, 1, 1, 12, 0, 0),
                    'ETag': '"abc123"'
                },
                {
                    'Key': 'file2.txt',
                    'Size': 200,
                    'LastModified': datetime(2024, 1, 2, 12, 0, 0),
                    'ETag': '"def456"'
                }
            ]
        }
        
        # List files
        files = connector.list_files()
        
        assert len(files) == 2
        assert files[0]['path'] == 'file1.txt'
        assert files[0]['size'] == 100
        assert files[0]['checksum'] == 'abc123'
        assert files[1]['path'] == 'file2.txt'
        assert files[1]['size'] == 200
        
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket',
            Prefix=''
        )
    
    def test_list_files_with_prefix(self, connector, mock_boto3):
        """Test listing with prefix filter."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock empty response
        mock_client.list_objects_v2.return_value = {'Contents': []}
        
        # List files with prefix
        files = connector.list_files(prefix='subfolder/')
        
        mock_client.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket',
            Prefix='subfolder/'
        )
    
    def test_list_files_empty(self, connector, mock_boto3):
        """Test listing when no files exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock empty response
        mock_client.list_objects_v2.return_value = {}
        
        # List files
        files = connector.list_files()
        
        assert files == []
    
    def test_list_files_not_connected(self, connector):
        """Test listing when not connected."""
        files = connector.list_files()
        
        assert files == []
    
    def test_list_files_client_error(self, connector, mock_boto3):
        """Test listing failure due to client error."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock client error
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.list_objects_v2.side_effect = Exception("List failed")
            
            # List files
            files = connector.list_files()
            
            assert files == []


class TestS3ConnectorMetadata:
    """Test file metadata operations."""
    
    def test_get_file_metadata_success(self, connector, mock_boto3):
        """Test successful metadata retrieval."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock head_object response
        mock_client.head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime(2024, 1, 1, 12, 0, 0),
            'Metadata': {'user': 'test_user', 'checksum': 'abc123'},
            'ETag': '"xyz789"',
            'ServerSideEncryption': 'AES256'
        }
        
        # Get metadata
        result = connector.get_file_metadata('remote/file.txt')
        
        assert result['success'] is True
        assert result['size'] == 1024
        assert result['metadata']['user'] == 'test_user'
        assert result['checksum'] == 'xyz789'
        assert result['encryption'] == 'AES256'
        
        mock_client.head_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='remote/file.txt'
        )
    
    def test_get_file_metadata_not_connected(self, connector):
        """Test metadata retrieval when not connected."""
        result = connector.get_file_metadata('remote/file.txt')
        
        assert result['success'] is False
        assert 'Not connected' in result['error']
    
    def test_get_file_metadata_client_error(self, connector, mock_boto3):
        """Test metadata failure due to client error."""
        # Setup mock
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3.resource.return_value = mock_resource
        connector.connect()
        
        # Mock client error
        with patch('src.connectors.s3_connector.ClientError', Exception):
            mock_client.head_object.side_effect = Exception("Not found")
            
            # Get metadata
            result = connector.get_file_metadata('remote/file.txt')
            
            assert result['success'] is False
            assert 'error' in result
