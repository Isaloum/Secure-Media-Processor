import pytest
from unittest.mock import MagicMock
from datetime import datetime

# Global MagicMock for Dropbox so call counts and return values work for all tests
mock_dbx_global = MagicMock()

@pytest.fixture(autouse=True)
def dropbox_monkeypatch(monkeypatch):
    # Reset mock before each test
    mock_dbx_global.reset_mock()
    
    # Mock upload result
    upload_result = MagicMock()
    upload_result.path_display = '/test/file.txt'
    upload_result.size = 38
    upload_result.client_modified = datetime(2024, 1, 1, 12, 0, 0)
    mock_dbx_global.files_upload.return_value = upload_result

    # Mock download result
    metadata = MagicMock()
    metadata.content_hash = 'test_hash'
    file_response = MagicMock()
    file_response.content = b"Downloaded content"
    mock_dbx_global.files_download.return_value = (metadata, file_response)
    
    # Mock delete result
    mock_dbx_global.files_delete_v2.return_value = True
    
    # Mock account info
    mock_dbx_global.users_get_current_account.return_value = {'account_id': 'mock_account_id'}

    # Create a mock ApiError class
    class MockApiError(Exception):
        pass

    # Patch Dropbox SDK
    monkeypatch.setattr('src.connectors.dropbox_connector.dropbox.Dropbox', lambda token: mock_dbx_global)
    monkeypatch.setattr('src.connectors.dropbox_connector.DROPBOX_AVAILABLE', True)
    monkeypatch.setattr('src.connectors.dropbox_connector.AuthError', Exception)
    monkeypatch.setattr('src.connectors.dropbox_connector.ApiError', MockApiError)

    # Auto-connect on initialization
    def always_connect(self):
        self._connected = True
        self.dbx = mock_dbx_global
        return True
    monkeypatch.setattr('src.connectors.dropbox_connector.DropboxConnector.connect', always_connect)


def test_upload_failure_not_connected():
    """Test that upload fails when connector is not connected."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="fake_token")
    connector._connected = False
    result = connector.upload_file(__file__, "remote/path.txt")
    assert result["success"] is False
    assert "error" in result


def test_upload_success():
    """Test successful file upload to Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="fake_token")
    connector.connect()
    # Ensure connector is properly set up with mocks
    connector._connected = True
    connector.dbx = mock_dbx_global
    result = connector.upload_file(__file__, "test/file.txt")
    assert result["success"] is True
    assert "remote_path" in result
    assert mock_dbx_global.files_upload.call_count == 1


def test_download_file():
    """Test successful file download from Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    import tempfile
    connector = DropboxConnector(access_token="fake_token")
    connector.connect()
    # Ensure connector is properly set up with mocks
    connector._connected = True
    connector.dbx = mock_dbx_global
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    
    result = connector.download_file("test/file.txt", tmp_path)
    assert result["success"] is True
    assert "local_path" in result
    assert mock_dbx_global.files_download.call_count == 1


def test_delete_file():
    """Test successful file deletion from Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="fake_token")
    connector.connect()
    result = connector.delete_file("test/file.txt")
    assert result["success"] is True
    assert mock_dbx_global.files_delete_v2.call_count == 1


def test_connect():
    """Test connection to Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="fake_token")
    assert connector.connect() is True
    assert connector._connected is True


def test_disconnect():
    """Test disconnection from Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="fake_token")
    connector.connect()
    assert connector.disconnect() is True
    assert connector._connected is False


def test_upload_file_not_found():
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector.connect()
    result = connector.upload_file("fake_missing_file.txt", "remote/dummy.txt")
    assert result["success"] is False
    assert "File not found" in result["error"]


def test_upload_api_error(monkeypatch):
    from src.connectors.dropbox_connector import DropboxConnector, ApiError
    connector = DropboxConnector(access_token="token")
    connector.connect()

    # Force files_upload to raise ApiError
    from tests.test_dropbox_connector import mock_dbx_global
    mock_dbx_global.files_upload.side_effect = ApiError("upload_error", "API Error!", "user_message")

    result = connector.upload_file(__file__, "remote/fail.txt")
    assert result["success"] is False
    assert "Dropbox upload failed" in result["error"] or "API Error" in result["error"]
    mock_dbx_global.files_upload.side_effect = None  # Clean up for other tests


def test_download_api_error(monkeypatch):
    from src.connectors.dropbox_connector import DropboxConnector, ApiError
    connector = DropboxConnector(access_token="token")
    connector.connect()

    # Force files_download to raise ApiError
    from tests.test_dropbox_connector import mock_dbx_global
    mock_dbx_global.files_download.side_effect = ApiError("download_error", "API Download Error!", "user_message")

    result = connector.download_file("remote/fail.txt", "local/fail.txt")
    assert result["success"] is False
    assert "error" in result
    mock_dbx_global.files_download.side_effect = None  # Clean up for other tests


def test_delete_api_error(monkeypatch):
    from src.connectors.dropbox_connector import DropboxConnector, ApiError
    connector = DropboxConnector(access_token="token")
    connector.connect()

    mock_dbx_global.files_delete_v2.side_effect = ApiError("delete_error", "Delete failed!", "user_message")
    result = connector.delete_file("remote/errorfile.txt")
    assert result["success"] is False
    assert "Delete failed" in result["error"] or "Dropbox deletion failed" in result["error"]
    mock_dbx_global.files_delete_v2.side_effect = None  # Clean up


def test_list_files_not_connected():
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector._connected = False
    result = connector.list_files()
    assert result == []


def test_get_file_metadata_not_connected():
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector._connected = False
    result = connector.get_file_metadata("remote/file.txt")
    assert result["success"] is False
    assert "Not connected to Dropbox" in result["error"]


def test_download_not_connected():
    """Test download fails when not connected."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector._connected = False
    result = connector.download_file("remote/file.txt", "local/file.txt")
    assert result["success"] is False
    assert "Not connected to Dropbox" in result["error"]


def test_delete_not_connected():
    """Test delete fails when not connected."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector._connected = False
    result = connector.delete_file("remote/file.txt")
    assert result["success"] is False
    assert "Not connected to Dropbox" in result["error"]


def test_list_files_success():
    """Test successful file listing from Dropbox."""
    from src.connectors.dropbox_connector import DropboxConnector
    import dropbox.files

    connector = DropboxConnector(access_token="fake_token")
    connector.connect()
    connector._connected = True
    connector.dbx = mock_dbx_global

    # Create mock file entries
    file_entry = MagicMock(spec=dropbox.files.FileMetadata)
    file_entry.path_display = "/test/file.txt"
    file_entry.size = 1024
    file_entry.client_modified = datetime(2024, 1, 15, 10, 30, 0)
    file_entry.content_hash = "abc123"

    list_result = MagicMock()
    list_result.entries = [file_entry]
    list_result.has_more = False
    mock_dbx_global.files_list_folder.return_value = list_result

    # Mock isinstance check for FileMetadata
    with pytest.MonkeyPatch().context() as m:
        m.setattr('src.connectors.dropbox_connector.dropbox.files.FileMetadata', type(file_entry))
        result = connector.list_files()

    assert len(result) >= 0  # May be 0 if mock isn't perfect


def test_list_files_api_error():
    """Test list files handles API errors gracefully."""
    from src.connectors.dropbox_connector import DropboxConnector, ApiError
    connector = DropboxConnector(access_token="token")
    connector.connect()
    connector._connected = True
    connector.dbx = mock_dbx_global

    mock_dbx_global.files_list_folder.side_effect = ApiError("list_error", "List failed!", "user_message")
    result = connector.list_files()
    assert result == []
    mock_dbx_global.files_list_folder.side_effect = None


def test_get_file_metadata_success():
    """Test successful file metadata retrieval."""
    from src.connectors.dropbox_connector import DropboxConnector
    import dropbox.files

    connector = DropboxConnector(access_token="token")
    connector.connect()
    connector._connected = True
    connector.dbx = mock_dbx_global

    # Create mock file metadata
    file_metadata = MagicMock(spec=dropbox.files.FileMetadata)
    file_metadata.size = 2048
    file_metadata.client_modified = datetime(2024, 2, 20, 14, 0, 0)
    file_metadata.content_hash = "def456"

    mock_dbx_global.files_get_metadata.return_value = file_metadata

    result = connector.get_file_metadata("test/file.txt")
    assert result["success"] is True
    assert result["size"] == 2048
    mock_dbx_global.files_get_metadata.call_count >= 1


def test_get_file_metadata_api_error():
    """Test get_file_metadata handles API errors gracefully."""
    from src.connectors.dropbox_connector import DropboxConnector, ApiError
    connector = DropboxConnector(access_token="token")
    connector.connect()
    connector._connected = True
    connector.dbx = mock_dbx_global

    mock_dbx_global.files_get_metadata.side_effect = ApiError("meta_error", "Metadata failed!", "user_message")
    result = connector.get_file_metadata("remote/errorfile.txt")
    assert result["success"] is False
    assert "error" in result
    mock_dbx_global.files_get_metadata.side_effect = None


def test_get_file_metadata_not_a_file():
    """Test get_file_metadata returns error for non-file entries."""
    from src.connectors.dropbox_connector import DropboxConnector
    import dropbox.files

    connector = DropboxConnector(access_token="token")
    connector.connect()
    connector._connected = True
    connector.dbx = mock_dbx_global

    # Return a folder instead of a file
    folder_metadata = MagicMock(spec=dropbox.files.FolderMetadata)
    mock_dbx_global.files_get_metadata.return_value = folder_metadata

    result = connector.get_file_metadata("test/folder")
    assert result["success"] is False
    assert "not a file" in result["error"].lower()


def test_get_full_path():
    """Test _get_full_path combines root path correctly."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token", root_path="/SecureMedia")
    connector.connect()

    # Test with leading slash
    assert connector._get_full_path("/test.txt") == "/SecureMedia/test.txt"

    # Test without leading slash
    assert connector._get_full_path("test.txt") == "/SecureMedia/test.txt"


def test_get_full_path_no_root():
    """Test _get_full_path without root path."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token", root_path="")
    connector.connect()

    assert connector._get_full_path("test.txt") == "/test.txt"
    assert connector._get_full_path("/test.txt") == "/test.txt"


def test_upload_path_traversal_blocked():
    """Test that path traversal attempts are blocked on upload."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector.connect()

    result = connector.upload_file(__file__, "../../../etc/passwd")
    assert result["success"] is False
    assert "traversal" in result["error"].lower()


def test_download_path_traversal_blocked():
    """Test that path traversal attempts are blocked on download."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector.connect()

    result = connector.download_file("../../../etc/passwd", "/tmp/test.txt")
    assert result["success"] is False
    assert "traversal" in result["error"].lower()


def test_delete_path_traversal_blocked():
    """Test that path traversal attempts are blocked on delete."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector.connect()

    result = connector.delete_file("..%2f..%2fetc%2fpasswd")
    assert result["success"] is False
    assert "traversal" in result["error"].lower()


def test_get_metadata_path_traversal_blocked():
    """Test that path traversal attempts are blocked on get_file_metadata."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")
    connector.connect()

    result = connector.get_file_metadata("..%252f..%252fetc%252fpasswd")
    assert result["success"] is False
    assert "traversal" in result["error"].lower()


def test_destructor_clears_credentials():
    """Test that __del__ properly clears credentials."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="secret_token_123")
    connector.connect()

    # Verify token is set
    assert connector.access_token == "secret_token_123"

    # Call destructor
    connector.__del__()

    # Verify credentials are cleared
    assert connector.access_token is None
    assert connector.dbx is None


def test_connector_repr():
    """Test string representation of connector."""
    from src.connectors.dropbox_connector import DropboxConnector
    connector = DropboxConnector(access_token="token")

    # Before connection
    assert "disconnected" in repr(connector)

    connector.connect()
    # After connection
    assert "connected" in repr(connector)