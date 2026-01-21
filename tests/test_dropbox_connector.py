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