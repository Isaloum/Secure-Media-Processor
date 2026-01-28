"""Tests for cloud storage module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from botocore.exceptions import ClientError

from src.cloud_storage import CloudStorageManager


@pytest.fixture
def mock_boto3(monkeypatch):
    """Global mock for boto3 client and resource."""
    mock_client = MagicMock()
    mock_resource = MagicMock()

    def mock_boto3_client(*args, **kwargs):
        return mock_client

    def mock_boto3_resource(*args, **kwargs):
        return mock_resource

    monkeypatch.setattr('src.cloud_storage.boto3.client', mock_boto3_client)
    monkeypatch.setattr('src.cloud_storage.boto3.resource', mock_boto3_resource)

    return {'client': mock_client, 'resource': mock_resource}


class TestCloudStorageManagerInit:
    """Test CloudStorageManager initialization."""

    def test_init_with_bucket_name(self, mock_boto3):
        """Test initialization with bucket name."""
        manager = CloudStorageManager(bucket_name='test-bucket')

        assert manager.bucket_name == 'test-bucket'
        assert manager.region == 'us-east-1'

    def test_init_with_custom_region(self, mock_boto3):
        """Test initialization with custom region."""
        manager = CloudStorageManager(
            bucket_name='test-bucket',
            region='eu-west-1'
        )

        assert manager.region == 'eu-west-1'

    def test_init_with_credentials(self, mock_boto3):
        """Test initialization with explicit credentials."""
        manager = CloudStorageManager(
            bucket_name='test-bucket',
            access_key='test-access-key',
            secret_key='test-secret-key'
        )

        assert manager.bucket_name == 'test-bucket'

    def test_init_creates_s3_client(self, mock_boto3):
        """Test that S3 client is created."""
        manager = CloudStorageManager(bucket_name='test-bucket')

        assert manager.s3_client is not None

    def test_init_creates_s3_resource(self, mock_boto3):
        """Test that S3 resource is created."""
        manager = CloudStorageManager(bucket_name='test-bucket')

        assert manager.s3_resource is not None


class TestUploadFile:
    """Test upload_file functionality."""

    def test_upload_file_success(self, mock_boto3, tmp_path):
        """Test successful file upload."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.upload_file(str(test_file))

        assert result['success'] is True
        assert result['remote_key'] == 'test.txt'
        assert 'checksum' in result
        assert 'size' in result
        mock_boto3['client'].upload_file.assert_called_once()

    def test_upload_file_with_custom_key(self, mock_boto3, tmp_path):
        """Test upload with custom remote key."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.upload_file(str(test_file), remote_key='custom/path/file.txt')

        assert result['success'] is True
        assert result['remote_key'] == 'custom/path/file.txt'

    def test_upload_file_with_metadata(self, mock_boto3, tmp_path):
        """Test upload with custom metadata."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.upload_file(
            str(test_file),
            metadata={'custom_key': 'custom_value'}
        )

        assert result['success'] is True
        # Verify metadata was passed to upload
        call_args = mock_boto3['client'].upload_file.call_args
        extra_args = call_args[1]['ExtraArgs']
        assert 'custom_key' in extra_args['Metadata']

    def test_upload_file_not_found(self, mock_boto3):
        """Test upload with non-existent file."""
        manager = CloudStorageManager(bucket_name='test-bucket')

        with pytest.raises(FileNotFoundError):
            manager.upload_file('/non/existent/file.txt')

    def test_upload_file_client_error(self, mock_boto3, tmp_path):
        """Test upload handling ClientError."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_boto3['client'].upload_file.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'upload_file'
        )

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.upload_file(str(test_file))

        assert result['success'] is False
        assert 'error' in result

    def test_upload_file_calculates_checksum(self, mock_boto3, tmp_path):
        """Test that checksum is calculated and included."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content for checksum")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.upload_file(str(test_file))

        assert 'checksum' in result
        assert len(result['checksum']) == 64  # SHA-256 hex length


class TestDownloadFile:
    """Test download_file functionality."""

    def test_download_file_success(self, mock_boto3, tmp_path):
        """Test successful file download."""
        mock_boto3['client'].head_object.return_value = {
            'Metadata': {'checksum': 'abc123'},
            'ContentLength': 100
        }

        manager = CloudStorageManager(bucket_name='test-bucket')
        download_path = tmp_path / "downloaded.txt"

        # Mock the download to create the file
        def create_file(*args, **kwargs):
            download_path.write_text("downloaded content")

        mock_boto3['client'].download_file.side_effect = create_file

        result = manager.download_file('remote/file.txt', str(download_path), verify_checksum=False)

        assert result['success'] is True
        assert result['local_path'] == str(download_path)
        mock_boto3['client'].download_file.assert_called_once()

    def test_download_file_creates_parent_dir(self, mock_boto3, tmp_path):
        """Test that parent directory is created."""
        mock_boto3['client'].head_object.return_value = {
            'Metadata': {},
            'ContentLength': 100
        }

        manager = CloudStorageManager(bucket_name='test-bucket')
        download_path = tmp_path / "nested" / "dir" / "file.txt"

        def create_file(*args, **kwargs):
            download_path.write_text("content")

        mock_boto3['client'].download_file.side_effect = create_file

        result = manager.download_file('remote.txt', str(download_path), verify_checksum=False)

        assert result['success'] is True
        assert download_path.parent.exists()

    def test_download_file_client_error(self, mock_boto3, tmp_path):
        """Test download handling ClientError."""
        mock_boto3['client'].head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
            'head_object'
        )

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.download_file('nonexistent.txt', str(tmp_path / "file.txt"))

        assert result['success'] is False
        assert 'error' in result


class TestDeleteFile:
    """Test delete_file functionality."""

    def test_delete_file_success(self, mock_boto3):
        """Test successful file deletion."""
        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.delete_file('file/to/delete.txt')

        assert result['success'] is True
        assert result['remote_key'] == 'file/to/delete.txt'
        mock_boto3['client'].delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='file/to/delete.txt'
        )

    def test_delete_file_client_error(self, mock_boto3):
        """Test delete handling ClientError."""
        mock_boto3['client'].delete_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'delete_object'
        )

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.delete_file('file.txt')

        assert result['success'] is False
        assert 'error' in result


class TestListFiles:
    """Test list_files functionality."""

    def test_list_files_success(self, mock_boto3):
        """Test successful file listing."""
        mock_boto3['client'].list_objects_v2.return_value = {
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

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.list_files()

        assert len(result) == 2
        assert result[0]['key'] == 'file1.txt'
        assert result[0]['size'] == 100
        assert result[1]['key'] == 'file2.txt'

    def test_list_files_with_prefix(self, mock_boto3):
        """Test listing with prefix filter."""
        mock_boto3['client'].list_objects_v2.return_value = {'Contents': []}

        manager = CloudStorageManager(bucket_name='test-bucket')
        manager.list_files(prefix='documents/')

        mock_boto3['client'].list_objects_v2.assert_called_with(
            Bucket='test-bucket',
            Prefix='documents/'
        )

    def test_list_files_empty(self, mock_boto3):
        """Test listing empty bucket."""
        mock_boto3['client'].list_objects_v2.return_value = {}

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.list_files()

        assert result == []

    def test_list_files_client_error(self, mock_boto3):
        """Test list handling ClientError."""
        mock_boto3['client'].list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'list_objects_v2'
        )

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.list_files()

        assert result == []


class TestSyncDirectory:
    """Test sync_directory functionality."""

    def test_sync_directory_success(self, mock_boto3, tmp_path):
        """Test successful directory sync."""
        # Create test directory structure
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.sync_directory(str(tmp_path))

        assert result['uploaded_count'] == 2
        assert result['failed_count'] == 0
        assert len(result['uploaded_files']) == 2

    def test_sync_directory_with_prefix(self, mock_boto3, tmp_path):
        """Test sync with remote prefix."""
        (tmp_path / "file.txt").write_text("content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.sync_directory(str(tmp_path), remote_prefix='backup')

        assert result['uploaded_count'] == 1
        assert 'backup/file.txt' in result['uploaded_files']

    def test_sync_directory_nested(self, mock_boto3, tmp_path):
        """Test sync with nested directory structure."""
        nested = tmp_path / "subdir"
        nested.mkdir()
        (tmp_path / "root.txt").write_text("root")
        (nested / "nested.txt").write_text("nested")

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.sync_directory(str(tmp_path))

        assert result['uploaded_count'] == 2

    def test_sync_directory_not_a_directory(self, mock_boto3, tmp_path):
        """Test sync with non-directory path."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        manager = CloudStorageManager(bucket_name='test-bucket')

        with pytest.raises(NotADirectoryError):
            manager.sync_directory(str(file_path))

    def test_sync_directory_partial_failure(self, mock_boto3, tmp_path):
        """Test sync with some upload failures."""
        (tmp_path / "good.txt").write_text("good")
        (tmp_path / "bad.txt").write_text("bad")

        # Fail on second upload
        call_count = [0]

        def upload_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ClientError(
                    {'Error': {'Code': 'Error', 'Message': 'Failed'}},
                    'upload_file'
                )

        mock_boto3['client'].upload_file.side_effect = upload_side_effect

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.sync_directory(str(tmp_path))

        assert result['uploaded_count'] == 1
        assert result['failed_count'] == 1


class TestGetFileMetadata:
    """Test get_file_metadata functionality."""

    def test_get_metadata_success(self, mock_boto3):
        """Test successful metadata retrieval."""
        mock_boto3['client'].head_object.return_value = {
            'ContentLength': 1024,
            'LastModified': datetime(2024, 1, 1, 12, 0, 0),
            'Metadata': {'custom': 'value'},
            'ServerSideEncryption': 'AES256'
        }

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.get_file_metadata('test.txt')

        assert result['success'] is True
        assert result['size'] == 1024
        assert result['metadata'] == {'custom': 'value'}
        assert result['encryption'] == 'AES256'

    def test_get_metadata_client_error(self, mock_boto3):
        """Test metadata retrieval with ClientError."""
        mock_boto3['client'].head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
            'head_object'
        )

        manager = CloudStorageManager(bucket_name='test-bucket')
        result = manager.get_file_metadata('nonexistent.txt')

        assert result['success'] is False
        assert 'error' in result


class TestCalculateChecksum:
    """Test checksum calculation."""

    def test_checksum_calculation(self, mock_boto3, tmp_path):
        """Test SHA-256 checksum calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("known content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        checksum = manager._calculate_checksum(test_file)

        # Verify it's a valid SHA-256 hex string
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

    def test_checksum_consistency(self, mock_boto3, tmp_path):
        """Test that same content produces same checksum."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("identical content")
        file2.write_text("identical content")

        manager = CloudStorageManager(bucket_name='test-bucket')
        checksum1 = manager._calculate_checksum(file1)
        checksum2 = manager._calculate_checksum(file2)

        assert checksum1 == checksum2

    def test_checksum_differs_for_different_content(self, mock_boto3, tmp_path):
        """Test that different content produces different checksum."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content A")
        file2.write_text("content B")

        manager = CloudStorageManager(bucket_name='test-bucket')
        checksum1 = manager._calculate_checksum(file1)
        checksum2 = manager._calculate_checksum(file2)

        assert checksum1 != checksum2
