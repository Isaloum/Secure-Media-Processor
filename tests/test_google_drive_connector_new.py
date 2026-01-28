import pytest
from unittest.mock import MagicMock, Mock
from datetime import datetime
from pathlib import Path

# Global MagicMock for Google Drive so call counts and return values work for all tests
mock_gdrive_service_global = MagicMock()

@pytest.fixture(autouse=True)
def google_drive_monkeypatch(monkeypatch):
    # Reset mock before each test
    mock_gdrive_service_global.reset_mock()
    
    # Mock credentials
    mock_credentials = MagicMock()
    
    # Mock service account credentials loading
    mock_service_account = MagicMock()
    mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
    
    # Mock build function to return our global service mock
    def mock_build(service_name, version, credentials):
        if service_name == 'drive' and version == 'v3':
            return mock_gdrive_service_global
        return MagicMock()
    
    # Mock about().get() for connection test
    mock_about = MagicMock()
    mock_about.get.return_value.execute.return_value = {'user': {'displayName': 'Test User'}}
    mock_gdrive_service_global.about.return_value = mock_about
    
    # Mock files().create() for upload
    mock_upload_result = {
        'id': 'file123',
        'name': 'test_file.txt',
        'size': 1234,
        'createdTime': '2024-01-01T12:00:00Z'
    }
    mock_files_create = MagicMock()
    mock_files_create.execute.return_value = mock_upload_result
    mock_gdrive_service_global.files.return_value.create.return_value = mock_files_create
    
    # Mock files().get() for metadata
    mock_file_metadata = {
        'id': 'file123',
        'name': 'test_file.txt',
        'size': '1234',
        'modifiedTime': '2024-01-01T12:00:00Z',
        'properties': {'checksum': 'test_checksum'},
        'md5Checksum': 'test_md5'
    }
    mock_files_get = MagicMock()
    mock_files_get.execute.return_value = mock_file_metadata
    mock_gdrive_service_global.files.return_value.get.return_value = mock_files_get
    
    # Mock files().get_media() for download
    mock_media = MagicMock()
    mock_gdrive_service_global.files.return_value.get_media.return_value = mock_media
    
    # Mock files().delete() for deletion
    mock_delete = MagicMock()
    mock_delete.execute.return_value = {}
    mock_gdrive_service_global.files.return_value.delete.return_value = mock_delete
    
    # Mock files().list() for listing
    mock_list_result = {
        'files': [
            {
                'id': 'file1',
                'name': 'file1.txt',
                'size': '100',
                'modifiedTime': '2024-01-01T12:00:00Z',
                'md5Checksum': 'checksum1'
            },
            {
                'id': 'file2',
                'name': 'file2.txt',
                'size': '200',
                'modifiedTime': '2024-01-02T12:00:00Z',
                'md5Checksum': 'checksum2'
            }
        ]
    }
    mock_files_list = MagicMock()
    mock_files_list.execute.return_value = mock_list_result
    mock_gdrive_service_global.files.return_value.list.return_value = mock_files_list
    
    # Create a mock HttpError class that matches the real one
    class MockHttpError(Exception):
        """Mock HttpError for testing."""
        def __init__(self, resp=None, content=b'', uri=''):
            self.resp = resp or MagicMock(status=500)
            self.content = content
            self.uri = uri
            super().__init__(str(content))

    # Patch Google Drive SDK
    monkeypatch.setattr('src.connectors.google_drive_connector.service_account', mock_service_account)
    monkeypatch.setattr('src.connectors.google_drive_connector.build', mock_build)
    monkeypatch.setattr('src.connectors.google_drive_connector.GOOGLE_AVAILABLE', True)
    monkeypatch.setattr('src.connectors.google_drive_connector.GoogleAuthError', Exception)
    monkeypatch.setattr('src.connectors.google_drive_connector.HttpError', MockHttpError)
    
    # Mock MediaFileUpload
    mock_media_upload = MagicMock()
    monkeypatch.setattr('src.connectors.google_drive_connector.MediaFileUpload', lambda *args, **kwargs: mock_media_upload)
    
    # Mock MediaIoBaseDownload
    class MockMediaDownloader:
        def __init__(self, fh, request):
            self.fh = fh
            self.request = request
            self.done = False
        
        def next_chunk(self):
            if not self.done:
                # Write some test content
                self.fh.write(b"test content")
                self.done = True
                return (MagicMock(progress=lambda: 1.0), True)
            return (MagicMock(progress=lambda: 1.0), True)
    
    monkeypatch.setattr('src.connectors.google_drive_connector.MediaIoBaseDownload', MockMediaDownloader)


def test_gdrive_connect():
    """Test connection to Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    # Create a temporary credentials file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        assert connector.connect() is True
        assert connector._connected is True
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_disconnect():
    """Test disconnection from Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        assert connector.disconnect() is True
        assert connector._connected is False
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_upload_success():
    """Test successful file upload to Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        result = connector.upload_file(__file__, "test_file.txt")
        assert result["success"] is True
        assert "file_id" in result
        assert mock_gdrive_service_global.files.return_value.create.call_count == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_upload_not_connected():
    """Test that upload fails when not connected."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector._connected = False
        result = connector.upload_file(__file__, "test_file.txt")
        assert result["success"] is False
        assert "Not connected to Google Drive" in result["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_upload_file_not_found():
    """Test upload fails when file doesn't exist."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        result = connector.upload_file("fake_missing_file.txt", "test.txt")
        assert result["success"] is False
        assert "File not found" in result["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_download_success():
    """Test successful file download from Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as cred_file:
        cred_file.write('{"type": "service_account"}')
        cred_path = cred_file.name
    
    with tempfile.NamedTemporaryFile(delete=False) as dl_file:
        dl_path = dl_file.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=cred_path)
        connector.connect()
        result = connector.download_file("test_file.txt", dl_path, verify_checksum=False)
        assert result["success"] is True
        assert "local_path" in result
    finally:
        Path(cred_path).unlink(missing_ok=True)
        Path(dl_path).unlink(missing_ok=True)


def test_gdrive_download_not_connected():
    """Test that download fails when not connected."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector._connected = False
        result = connector.download_file("test_file.txt", "/tmp/local.txt")
        assert result["success"] is False
        assert "Not connected to Google Drive" in result["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_delete_success():
    """Test successful file deletion from Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        result = connector.delete_file("test_file.txt")
        assert result["success"] is True
        assert mock_gdrive_service_global.files.return_value.delete.call_count == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_delete_not_connected():
    """Test that delete fails when not connected."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector._connected = False
        result = connector.delete_file("test_file.txt")
        assert result["success"] is False
        assert "Not connected to Google Drive" in result["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_list_files_success():
    """Test listing files in Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        result = connector.list_files()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['path'] == 'file1.txt'
        assert mock_gdrive_service_global.files.return_value.list.call_count == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_list_files_not_connected():
    """Test that list_files fails when not connected."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector._connected = False
        result = connector.list_files()
        assert result == []
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_get_file_metadata_success():
    """Test getting file metadata from Google Drive."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()
        result = connector.get_file_metadata("test_file.txt")
        assert result["success"] is True
        assert "size" in result
        assert result["size"] == 1234
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_get_file_metadata_not_connected():
    """Test that get_file_metadata fails when not connected."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name
    
    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector._connected = False
        result = connector.get_file_metadata("test_file.txt")
        assert result["success"] is False
        assert "Not connected to Google Drive" in result["error"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_upload_api_error():
    """Test upload handles API errors properly."""
    from src.connectors.google_drive_connector import GoogleDriveConnector, HttpError
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name

    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()

        # Force create to raise HttpError
        mock_gdrive_service_global.files.return_value.create.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"API Error!"
        )

        result = connector.upload_file(__file__, "test_file.txt")
        assert result["success"] is False
        assert "error" in result

        # Clean up
        mock_gdrive_service_global.files.return_value.create.return_value.execute.side_effect = None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_download_api_error():
    """Test download handles API errors properly."""
    from src.connectors.google_drive_connector import GoogleDriveConnector, HttpError
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name

    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()

        # Force get to raise HttpError
        mock_gdrive_service_global.files.return_value.get.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Download Error!"
        )

        result = connector.download_file("test_file.txt", "/tmp/local.txt")
        assert result["success"] is False
        assert "error" in result

        # Clean up
        mock_gdrive_service_global.files.return_value.get.return_value.execute.side_effect = None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_delete_api_error():
    """Test delete handles API errors properly."""
    from src.connectors.google_drive_connector import GoogleDriveConnector, HttpError
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write('{"type": "service_account"}')
        tmp_path = tmp.name

    try:
        connector = GoogleDriveConnector(credentials_path=tmp_path)
        connector.connect()

        # Force delete to raise HttpError
        mock_gdrive_service_global.files.return_value.delete.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b"Delete Error!"
        )

        result = connector.delete_file("test_file.txt")
        assert result["success"] is False
        assert "error" in result

        # Clean up
        mock_gdrive_service_global.files.return_value.delete.return_value.execute.side_effect = None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_gdrive_connect_no_credentials():
    """Test connection fails when credentials file doesn't exist."""
    from src.connectors.google_drive_connector import GoogleDriveConnector
    
    connector = GoogleDriveConnector(credentials_path="/fake/path/credentials.json")
    assert connector.connect() is False
    assert connector._connected is False
