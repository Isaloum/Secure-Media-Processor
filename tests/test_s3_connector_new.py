import pytest
from unittest.mock import MagicMock
from datetime import datetime

# Global MagicMock for S3 so call counts and return values work for all tests
mock_s3_client_global = MagicMock()
mock_s3_resource_global = MagicMock()

@pytest.fixture(autouse=True)
def s3_monkeypatch(monkeypatch):
    # Reset mocks before each test
    mock_s3_client_global.reset_mock()
    mock_s3_resource_global.reset_mock()
    
    # Mock head_bucket for connection test
    mock_s3_client_global.head_bucket.return_value = {}
    
    # Mock upload_file
    mock_s3_client_global.upload_file.return_value = None
    
    # Mock head_object for download
    mock_s3_client_global.head_object.return_value = {
        'Metadata': {'checksum': 'test_checksum'},
        'ContentLength': 123,
        'LastModified': datetime(2024, 1, 1, 12, 0, 0)
    }
    
    # Mock download_file
    mock_s3_client_global.download_file.return_value = None
    
    # Mock delete_object
    mock_s3_client_global.delete_object.return_value = {'DeleteMarker': True}
    
    # Mock list_objects_v2
    mock_s3_client_global.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'remote/file1.txt',
                'Size': 123,
                'LastModified': datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                'Key': 'remote/file2.txt',
                'Size': 456,
                'LastModified': datetime(2024, 1, 2, 12, 0, 0)
            }
        ]
    }
    
    # Mock boto3.client to return our global mock
    def mock_boto3_client(service_name, **kwargs):
        if service_name == 's3':
            return mock_s3_client_global
        return MagicMock()
    
    # Mock boto3.resource to return our global mock
    def mock_boto3_resource(service_name, **kwargs):
        if service_name == 's3':
            return mock_s3_resource_global
        return MagicMock()
    
    # Patch boto3
    monkeypatch.setattr('src.connectors.s3_connector.boto3.client', mock_boto3_client)
    monkeypatch.setattr('src.connectors.s3_connector.boto3.resource', mock_boto3_resource)
    
    # Create mock ClientError for error tests
    class MockClientError(Exception):
        pass
    
    monkeypatch.setattr('src.connectors.s3_connector.ClientError', MockClientError)
    monkeypatch.setattr('src.connectors.s3_connector.NoCredentialsError', Exception)


def test_s3_connect():
    """Test connection to S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        region="us-east-1",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    assert connector.connect() is True
    assert connector._connected is True
    assert mock_s3_client_global.head_bucket.call_count == 1


def test_s3_disconnect():
    """Test disconnection from S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    assert connector.disconnect() is True
    assert connector._connected is False


def test_s3_upload_success():
    """Test successful file upload to S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    result = connector.upload_file(__file__, "remote/file.txt")
    assert result["success"] is True
    assert "remote_path" in result
    assert mock_s3_client_global.upload_file.call_count == 1


def test_s3_upload_not_connected():
    """Test that upload fails when not connected."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector._connected = False
    result = connector.upload_file(__file__, "remote/file.txt")
    assert result["success"] is False
    assert "Not connected to S3" in result["error"]


def test_s3_upload_file_not_found():
    """Test upload fails when file doesn't exist."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    result = connector.upload_file("fake_missing_file.txt", "remote/file.txt")
    assert result["success"] is False
    assert "File not found" in result["error"]


def test_s3_download_success():
    """Test successful file download from S3."""
    from src.connectors.s3_connector import S3Connector
    import tempfile
    from pathlib import Path
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    
    # Mock download_file to actually create the file
    def mock_download(bucket, key, local_path):
        Path(local_path).write_text("test content")
    
    mock_s3_client_global.download_file.side_effect = mock_download
    
    result = connector.download_file("remote/file.txt", tmp_path, verify_checksum=False)
    assert result["success"] is True
    assert mock_s3_client_global.download_file.call_count == 1
    
    # Clean up
    mock_s3_client_global.download_file.side_effect = None
    Path(tmp_path).unlink(missing_ok=True)


def test_s3_download_not_connected():
    """Test that download fails when not connected."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector._connected = False
    result = connector.download_file("remote/file.txt", "/tmp/local.txt")
    assert result["success"] is False
    assert "Not connected to S3" in result["error"]


def test_s3_delete_success():
    """Test successful file deletion from S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    result = connector.delete_file("remote/file.txt")
    assert result["success"] is True
    assert mock_s3_client_global.delete_object.call_count == 1


def test_s3_delete_not_connected():
    """Test that delete fails when not connected."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector._connected = False
    result = connector.delete_file("remote/file.txt")
    assert result["success"] is False
    assert "Not connected to S3" in result["error"]


def test_s3_list_files_success():
    """Test listing files in S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    result = connector.list_files()
    assert isinstance(result, list)
    assert len(result) == 2
    assert mock_s3_client_global.list_objects_v2.call_count == 1


def test_s3_list_files_not_connected():
    """Test that list_files fails when not connected."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector._connected = False
    result = connector.list_files()
    assert result == []


def test_s3_get_file_metadata_success():
    """Test getting file metadata from S3."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    result = connector.get_file_metadata("remote/file.txt")
    assert result["success"] is True
    assert "size" in result
    assert mock_s3_client_global.head_object.call_count >= 1


def test_s3_get_file_metadata_not_connected():
    """Test that get_file_metadata fails when not connected."""
    from src.connectors.s3_connector import S3Connector
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector._connected = False
    result = connector.get_file_metadata("remote/file.txt")
    assert result["success"] is False
    assert "Not connected to S3" in result["error"]


def test_s3_upload_api_error():
    """Test upload handles API errors properly."""
    from src.connectors.s3_connector import S3Connector, ClientError
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    
    # Force upload_file to raise ClientError
    from tests.test_s3_connector_new import mock_s3_client_global
    mock_s3_client_global.upload_file.side_effect = ClientError(
        {'Error': {'Code': '500', 'Message': 'Server Error'}},
        'upload_file'
    )
    
    result = connector.upload_file(__file__, "remote/file.txt")
    assert result["success"] is False
    assert "error" in result
    mock_s3_client_global.upload_file.side_effect = None  # Clean up


def test_s3_download_api_error():
    """Test download handles API errors properly."""
    from src.connectors.s3_connector import S3Connector, ClientError
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    
    # Force download_file to raise ClientError
    from tests.test_s3_connector_new import mock_s3_client_global
    mock_s3_client_global.download_file.side_effect = ClientError(
        {'Error': {'Code': '404', 'Message': 'Not Found'}},
        'download_file'
    )
    
    result = connector.download_file("remote/file.txt", "/tmp/local.txt")
    assert result["success"] is False
    assert "error" in result
    mock_s3_client_global.download_file.side_effect = None  # Clean up


def test_s3_delete_api_error():
    """Test delete handles API errors properly."""
    from src.connectors.s3_connector import S3Connector, ClientError
    connector = S3Connector(
        bucket_name="test-bucket",
        access_key="AKIAFAKE",
        secret_key="secret123"
    )
    connector.connect()
    
    # Force delete_object to raise ClientError
    from tests.test_s3_connector_new import mock_s3_client_global
    mock_s3_client_global.delete_object.side_effect = ClientError(
        {'Error': {'Code': '403', 'Message': 'Forbidden'}},
        'delete_object'
    )
    
    result = connector.delete_file("remote/file.txt")
    assert result["success"] is False
    assert "error" in result
    mock_s3_client_global.delete_object.side_effect = None  # Clean up
