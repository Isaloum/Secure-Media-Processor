"""Test suite for S3 connector."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, NoCredentialsError
from src.connectors.s3_connector import S3Connector


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client."""
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource:
        yield mock_client, mock_resource


@pytest.fixture
def s3_connector():
    """Create S3 connector instance."""
    return S3Connector(
        bucket_name='test-bucket',
        region='us-east-1',
        access_key='test-key',
        secret_key='test-secret'
    )


def test_s3_connector_initialization():
    """Test S3 connector initialization."""
    connector = S3Connector(
        bucket_name='my-bucket',
        region='us-west-2',
        encryption='AES256'
    )
    
    assert connector.bucket_name == 'my-bucket'
    assert connector.region == 'us-west-2'
    assert connector.encryption == 'AES256'
    assert not connector.is_connected()


def test_connect_success(s3_connector, mock_boto3_client):
    """Test successful connection to S3."""
    mock_client, mock_resource = mock_boto3_client
    mock_s3_client = Mock()
    mock_client.return_value = mock_s3_client
    
    result = s3_connector.connect()
    
    assert result is True
    assert s3_connector.is_connected()
    mock_s3_client.head_bucket.assert_called_once_with(Bucket='test-bucket')


def test_connect_failure(s3_connector, mock_boto3_client):
    """Test failed connection to S3."""
    mock_client, mock_resource = mock_boto3_client
    mock_s3_client = Mock()
    mock_s3_client.head_bucket.side_effect = NoCredentialsError()
    mock_client.return_value = mock_s3_client
    
    result = s3_connector.connect()
    
    assert result is False
    assert not s3_connector.is_connected()


def test_disconnect(s3_connector):
    """Test disconnection from S3."""
    s3_connector._connected = True
    
    result = s3_connector.disconnect()
    
    assert result is True
    assert not s3_connector.is_connected()


def test_upload_file_not_connected(s3_connector, tmp_path):
    """Test upload when not connected."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = s3_connector.upload_file(test_file, "remote/test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_upload_file_not_found(s3_connector):
    """Test upload with non-existent file."""
    s3_connector._connected = True
    
    result = s3_connector.upload_file("/nonexistent/file.txt", "remote/test.txt")
    
    assert result['success'] is False
    assert 'File not found' in result['error']


def test_upload_file_success(s3_connector, tmp_path, mock_boto3_client):
    """Test successful file upload."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = s3_connector.upload_file(test_file, "remote/test.txt")
    
    assert result['success'] is True
    assert result['remote_path'] == "remote/test.txt"
    assert 'checksum' in result
    assert result['size'] > 0
    mock_s3_client.upload_file.assert_called_once()


def test_download_file_not_connected(s3_connector, tmp_path):
    """Test download when not connected."""
    local_path = tmp_path / "downloaded.txt"
    
    result = s3_connector.download_file("remote/test.txt", local_path)
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_download_file_success(s3_connector, tmp_path, mock_boto3_client):
    """Test successful file download."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_s3_client.head_object.return_value = {
        'Metadata': {'checksum': 'abc123'}
    }
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    local_path = tmp_path / "downloaded.txt"
    
    # Mock the download to create a file
    def mock_download(bucket, key, path):
        Path(path).write_text("test content")
    
    mock_s3_client.download_file.side_effect = mock_download
    
    with patch.object(s3_connector, '_calculate_checksum', return_value='abc123'):
        result = s3_connector.download_file("remote/test.txt", local_path)
    
    assert result['success'] is True
    assert result['checksum_verified'] is True
    assert local_path.exists()


def test_download_file_checksum_mismatch(s3_connector, tmp_path, mock_boto3_client):
    """Test download with checksum verification failure."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_s3_client.head_object.return_value = {
        'Metadata': {'checksum': 'expected_checksum'}
    }
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    local_path = tmp_path / "downloaded.txt"
    
    def mock_download(bucket, key, path):
        Path(path).write_text("test content")
    
    mock_s3_client.download_file.side_effect = mock_download
    
    with patch.object(s3_connector, '_calculate_checksum', return_value='wrong_checksum'):
        result = s3_connector.download_file("remote/test.txt", local_path, verify_checksum=True)
    
    assert result['success'] is False
    assert 'Checksum verification failed' in result['error']
    assert not local_path.exists()


def test_delete_file_not_connected(s3_connector):
    """Test delete when not connected."""
    result = s3_connector.delete_file("remote/test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_delete_file_success(s3_connector, mock_boto3_client):
    """Test successful file deletion."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    result = s3_connector.delete_file("remote/test.txt")
    
    assert result['success'] is True
    assert result['remote_path'] == "remote/test.txt"
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket='test-bucket',
        Key='remote/test.txt'
    )


def test_list_files_not_connected(s3_connector):
    """Test list files when not connected."""
    result = s3_connector.list_files()
    
    assert result == []


def test_list_files_success(s3_connector, mock_boto3_client):
    """Test successful file listing."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_s3_client.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'file1.txt',
                'Size': 100,
                'LastModified': MagicMock(),
                'ETag': '"abc123"'
            },
            {
                'Key': 'file2.txt',
                'Size': 200,
                'LastModified': MagicMock(),
                'ETag': '"def456"'
            }
        ]
    }
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    result = s3_connector.list_files(prefix='test/')
    
    assert len(result) == 2
    assert result[0]['path'] == 'file1.txt'
    assert result[0]['size'] == 100
    assert result[1]['path'] == 'file2.txt'


def test_get_file_metadata_not_connected(s3_connector):
    """Test get metadata when not connected."""
    result = s3_connector.get_file_metadata("remote/test.txt")
    
    assert result['success'] is False
    assert 'Not connected' in result['error']


def test_get_file_metadata_success(s3_connector, mock_boto3_client):
    """Test successful metadata retrieval."""
    mock_client, _ = mock_boto3_client
    mock_s3_client = Mock()
    mock_s3_client.head_object.return_value = {
        'ContentLength': 1024,
        'LastModified': MagicMock(),
        'Metadata': {'custom': 'value'},
        'ETag': '"abc123"',
        'ServerSideEncryption': 'AES256'
    }
    mock_client.return_value = mock_s3_client
    s3_connector.connect()
    
    result = s3_connector.get_file_metadata("remote/test.txt")
    
    assert result['success'] is True
    assert result['size'] == 1024
    assert result['metadata'] == {'custom': 'value'}
    assert result['encryption'] == 'AES256'
