"""Test suite for ConnectorManager with mocked connectors."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import tempfile

from src.connectors.connector_manager import ConnectorManager
from src.connectors.base_connector import CloudConnector


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a test file.")
    return file_path


@pytest.fixture
def mock_connector():
    """Create a mock CloudConnector."""
    connector = MagicMock(spec=CloudConnector)
    connector.get_provider_name.return_value = 'MockCloud'
    connector.is_connected.return_value = False
    connector.connect.return_value = True
    connector.disconnect.return_value = True
    return connector


@pytest.fixture
def manager():
    """Create a ConnectorManager instance."""
    return ConnectorManager()


class TestConnectorManagerInit:
    """Test initialization of ConnectorManager."""
    
    def test_init(self):
        """Test manager initialization."""
        manager = ConnectorManager()
        
        assert manager.connectors == {}
        assert manager.active_connector_name is None
    
    def test_repr(self, manager, mock_connector):
        """Test string representation."""
        # Empty manager
        assert "connectors=0" in repr(manager)
        assert "active='None'" in repr(manager)
        
        # With connectors
        manager.add_connector('test', mock_connector)
        assert "connectors=1" in repr(manager)
        assert "active='test'" in repr(manager)


class TestConnectorManagerAdd:
    """Test adding connectors."""
    
    def test_add_connector(self, manager, mock_connector):
        """Test adding a connector."""
        result = manager.add_connector('s3', mock_connector)
        
        assert result is True
        assert 's3' in manager.connectors
        assert manager.connectors['s3'] == mock_connector
        assert manager.active_connector_name == 's3'
    
    def test_add_multiple_connectors(self, manager):
        """Test adding multiple connectors."""
        mock_s3 = MagicMock(spec=CloudConnector)
        mock_s3.get_provider_name.return_value = 'S3'
        
        mock_dropbox = MagicMock(spec=CloudConnector)
        mock_dropbox.get_provider_name.return_value = 'Dropbox'
        
        manager.add_connector('s3', mock_s3)
        manager.add_connector('dropbox', mock_dropbox)
        
        assert len(manager.connectors) == 2
        assert 's3' in manager.connectors
        assert 'dropbox' in manager.connectors
        assert manager.active_connector_name == 's3'  # First one stays active
    
    def test_add_connector_replace_existing(self, manager, mock_connector):
        """Test replacing an existing connector."""
        manager.add_connector('test', mock_connector)
        
        new_connector = MagicMock(spec=CloudConnector)
        new_connector.get_provider_name.return_value = 'NewCloud'
        
        result = manager.add_connector('test', new_connector)
        
        assert result is True
        assert manager.connectors['test'] == new_connector


class TestConnectorManagerRemove:
    """Test removing connectors."""
    
    def test_remove_connector(self, manager, mock_connector):
        """Test removing a connector."""
        manager.add_connector('test', mock_connector)
        
        result = manager.remove_connector('test')
        
        assert result is True
        assert 'test' not in manager.connectors
        assert manager.active_connector_name is None
        mock_connector.disconnect.assert_not_called()  # Not connected
    
    def test_remove_connected_connector(self, manager, mock_connector):
        """Test removing a connected connector."""
        mock_connector.is_connected.return_value = True
        manager.add_connector('test', mock_connector)
        
        result = manager.remove_connector('test')
        
        assert result is True
        mock_connector.disconnect.assert_called_once()
    
    def test_remove_nonexistent_connector(self, manager):
        """Test removing a connector that doesn't exist."""
        result = manager.remove_connector('nonexistent')
        
        assert result is False
    
    def test_remove_active_connector_sets_new_active(self, manager):
        """Test that removing active connector sets a new active one."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.get_provider_name.return_value = 'Cloud1'
        mock2 = MagicMock(spec=CloudConnector)
        mock2.get_provider_name.return_value = 'Cloud2'
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        # cloud1 is active
        assert manager.active_connector_name == 'cloud1'
        
        # Remove cloud1
        manager.remove_connector('cloud1')
        
        # cloud2 should become active
        assert manager.active_connector_name == 'cloud2'


class TestConnectorManagerGet:
    """Test getting connectors."""
    
    def test_get_connector(self, manager, mock_connector):
        """Test getting a connector by name."""
        manager.add_connector('test', mock_connector)
        
        connector = manager.get_connector('test')
        
        assert connector == mock_connector
    
    def test_get_nonexistent_connector(self, manager):
        """Test getting a connector that doesn't exist."""
        connector = manager.get_connector('nonexistent')
        
        assert connector is None
    
    def test_get_active_connector(self, manager, mock_connector):
        """Test getting the active connector."""
        manager.add_connector('test', mock_connector)
        
        connector = manager.get_active_connector()
        
        assert connector == mock_connector
    
    def test_get_active_connector_none(self, manager):
        """Test getting active connector when none set."""
        connector = manager.get_active_connector()
        
        assert connector is None


class TestConnectorManagerSetActive:
    """Test setting active connector."""
    
    def test_set_active(self, manager):
        """Test setting active connector."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.get_provider_name.return_value = 'Cloud1'
        mock2 = MagicMock(spec=CloudConnector)
        mock2.get_provider_name.return_value = 'Cloud2'
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        result = manager.set_active('cloud2')
        
        assert result is True
        assert manager.active_connector_name == 'cloud2'
    
    def test_set_active_nonexistent(self, manager):
        """Test setting nonexistent connector as active."""
        result = manager.set_active('nonexistent')
        
        assert result is False


class TestConnectorManagerList:
    """Test listing connectors."""
    
    def test_list_connectors_empty(self, manager):
        """Test listing when no connectors exist."""
        connectors = manager.list_connectors()
        
        assert connectors == []
    
    def test_list_connectors(self, manager):
        """Test listing connectors."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.get_provider_name.return_value = 'S3'
        mock1.is_connected.return_value = True
        
        mock2 = MagicMock(spec=CloudConnector)
        mock2.get_provider_name.return_value = 'Dropbox'
        mock2.is_connected.return_value = False
        
        manager.add_connector('s3', mock1)
        manager.add_connector('dropbox', mock2)
        
        connectors = manager.list_connectors()
        
        assert len(connectors) == 2
        
        # Check s3 info
        s3_info = next(c for c in connectors if c['name'] == 's3')
        assert s3_info['provider'] == 'S3'
        assert s3_info['connected'] is True
        assert s3_info['active'] is True
        
        # Check dropbox info
        dropbox_info = next(c for c in connectors if c['name'] == 'dropbox')
        assert dropbox_info['provider'] == 'Dropbox'
        assert dropbox_info['connected'] is False
        assert dropbox_info['active'] is False


class TestConnectorManagerConnectAll:
    """Test connecting all connectors."""
    
    def test_connect_all(self, manager):
        """Test connecting all connectors."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.is_connected.return_value = False
        mock1.connect.return_value = True
        
        mock2 = MagicMock(spec=CloudConnector)
        mock2.is_connected.return_value = False
        mock2.connect.return_value = True
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        results = manager.connect_all()
        
        assert results == {'cloud1': True, 'cloud2': True}
        mock1.connect.assert_called_once()
        mock2.connect.assert_called_once()
    
    def test_connect_all_skip_connected(self, manager):
        """Test that already connected connectors are skipped."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.is_connected.return_value = True
        
        mock2 = MagicMock(spec=CloudConnector)
        mock2.is_connected.return_value = False
        mock2.connect.return_value = True
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        results = manager.connect_all()
        
        assert results == {'cloud1': True, 'cloud2': True}
        mock1.connect.assert_not_called()  # Already connected
        mock2.connect.assert_called_once()


class TestConnectorManagerDisconnectAll:
    """Test disconnecting all connectors."""
    
    def test_disconnect_all(self, manager):
        """Test disconnecting all connectors."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.is_connected.return_value = True
        mock1.disconnect.return_value = True
        
        mock2 = MagicMock(spec=CloudConnector)
        mock2.is_connected.return_value = True
        mock2.disconnect.return_value = True
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        results = manager.disconnect_all()
        
        assert results == {'cloud1': True, 'cloud2': True}
        mock1.disconnect.assert_called_once()
        mock2.disconnect.assert_called_once()
    
    def test_disconnect_all_skip_disconnected(self, manager):
        """Test that already disconnected connectors are skipped."""
        mock1 = MagicMock(spec=CloudConnector)
        mock1.is_connected.return_value = False
        
        mock2 = MagicMock(spec=CloudConnector)
        mock2.is_connected.return_value = True
        mock2.disconnect.return_value = True
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        results = manager.disconnect_all()
        
        assert results == {'cloud1': True, 'cloud2': True}
        mock1.disconnect.assert_not_called()  # Already disconnected
        mock2.disconnect.assert_called_once()


class TestConnectorManagerOperations:
    """Test file operations through manager."""
    
    def test_upload_file_with_active(self, manager, mock_connector, sample_file):
        """Test uploading file using active connector."""
        mock_connector.upload_file.return_value = {
            'success': True,
            'remote_path': 'file.txt'
        }
        
        manager.add_connector('test', mock_connector)
        
        result = manager.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is True
        mock_connector.upload_file.assert_called_once_with(sample_file, 'file.txt', None)
    
    def test_upload_file_with_specific_connector(self, manager, sample_file):
        """Test uploading file using specific connector."""
        mock1 = MagicMock(spec=CloudConnector)
        mock2 = MagicMock(spec=CloudConnector)
        mock2.upload_file.return_value = {'success': True}
        
        manager.add_connector('cloud1', mock1)
        manager.add_connector('cloud2', mock2)
        
        result = manager.upload_file(sample_file, 'file.txt', connector_name='cloud2')
        
        assert result['success'] is True
        mock1.upload_file.assert_not_called()
        mock2.upload_file.assert_called_once()
    
    def test_upload_file_no_connector(self, manager, sample_file):
        """Test uploading when no connector available."""
        result = manager.upload_file(sample_file, 'file.txt')
        
        assert result['success'] is False
        assert 'No connector available' in result['error']
    
    def test_download_file_with_active(self, manager, mock_connector, temp_dir):
        """Test downloading file using active connector."""
        local_path = temp_dir / "downloaded.txt"
        mock_connector.download_file.return_value = {
            'success': True,
            'local_path': str(local_path)
        }
        
        manager.add_connector('test', mock_connector)
        
        result = manager.download_file('file.txt', local_path)
        
        assert result['success'] is True
        mock_connector.download_file.assert_called_once_with('file.txt', local_path, True)
    
    def test_delete_file_with_active(self, manager, mock_connector):
        """Test deleting file using active connector."""
        mock_connector.delete_file.return_value = {'success': True}
        
        manager.add_connector('test', mock_connector)
        
        result = manager.delete_file('file.txt')
        
        assert result['success'] is True
        mock_connector.delete_file.assert_called_once_with('file.txt')
    
    def test_list_files_with_active(self, manager, mock_connector):
        """Test listing files using active connector."""
        mock_connector.list_files.return_value = [
            {'path': 'file1.txt'},
            {'path': 'file2.txt'}
        ]
        
        manager.add_connector('test', mock_connector)
        
        files = manager.list_files()
        
        assert len(files) == 2
        mock_connector.list_files.assert_called_once_with('')
    
    def test_list_files_with_prefix(self, manager, mock_connector):
        """Test listing files with prefix."""
        mock_connector.list_files.return_value = []
        
        manager.add_connector('test', mock_connector)
        
        files = manager.list_files(prefix='subfolder/')
        
        mock_connector.list_files.assert_called_once_with('subfolder/')
    
    def test_get_file_metadata_with_active(self, manager, mock_connector):
        """Test getting file metadata using active connector."""
        mock_connector.get_file_metadata.return_value = {
            'success': True,
            'size': 1024
        }
        
        manager.add_connector('test', mock_connector)
        
        result = manager.get_file_metadata('file.txt')
        
        assert result['success'] is True
        mock_connector.get_file_metadata.assert_called_once_with('file.txt')


class TestConnectorManagerSync:
    """Test file synchronization across connectors."""
    
    def test_sync_file_across_connectors(self, manager, temp_dir):
        """Test syncing file from source to multiple targets."""
        # Create mock connectors
        mock_source = MagicMock(spec=CloudConnector)
        mock_target1 = MagicMock(spec=CloudConnector)
        mock_target2 = MagicMock(spec=CloudConnector)
        
        # Mock download from source
        def mock_download(remote_path, local_path):
            Path(local_path).write_text("File content")
            return {'success': True}
        
        mock_source.download_file.side_effect = mock_download
        
        # Mock upload to targets
        mock_target1.upload_file.return_value = {'success': True}
        mock_target2.upload_file.return_value = {'success': True}
        
        # Add connectors
        manager.add_connector('source', mock_source)
        manager.add_connector('target1', mock_target1)
        manager.add_connector('target2', mock_target2)
        
        # Sync file
        result = manager.sync_file_across_connectors(
            'file.txt',
            'source',
            ['target1', 'target2']
        )
        
        assert result['success'] is True
        assert result['results']['target1']['success'] is True
        assert result['results']['target2']['success'] is True
        
        mock_source.download_file.assert_called_once()
        mock_target1.upload_file.assert_called_once()
        mock_target2.upload_file.assert_called_once()
    
    def test_sync_file_source_not_found(self, manager):
        """Test syncing when source connector doesn't exist."""
        result = manager.sync_file_across_connectors(
            'file.txt',
            'nonexistent',
            ['target']
        )
        
        assert result['success'] is False
        assert 'not found' in result['error']
    
    def test_sync_file_download_failure(self, manager):
        """Test syncing when download from source fails."""
        mock_source = MagicMock(spec=CloudConnector)
        mock_source.download_file.return_value = {
            'success': False,
            'error': 'Download failed'
        }
        
        manager.add_connector('source', mock_source)
        
        result = manager.sync_file_across_connectors(
            'file.txt',
            'source',
            ['target']
        )
        
        assert result['success'] is False
        assert 'Failed to download from source' in result['error']
    
    def test_sync_file_target_not_found(self, manager, temp_dir):
        """Test syncing when target connector doesn't exist."""
        mock_source = MagicMock(spec=CloudConnector)
        
        def mock_download(remote_path, local_path):
            Path(local_path).write_text("File content")
            return {'success': True}
        
        mock_source.download_file.side_effect = mock_download
        
        manager.add_connector('source', mock_source)
        
        result = manager.sync_file_across_connectors(
            'file.txt',
            'source',
            ['nonexistent']
        )
        
        assert result['success'] is False
        assert result['results']['nonexistent']['success'] is False
        assert 'not found' in result['results']['nonexistent']['error']
    
    def test_sync_file_partial_success(self, manager, temp_dir):
        """Test syncing with partial success (one target fails)."""
        mock_source = MagicMock(spec=CloudConnector)
        mock_target1 = MagicMock(spec=CloudConnector)
        mock_target2 = MagicMock(spec=CloudConnector)
        
        # Mock download from source
        def mock_download(remote_path, local_path):
            Path(local_path).write_text("File content")
            return {'success': True}
        
        mock_source.download_file.side_effect = mock_download
        
        # Mock upload - one succeeds, one fails
        mock_target1.upload_file.return_value = {'success': True}
        mock_target2.upload_file.return_value = {
            'success': False,
            'error': 'Upload failed'
        }
        
        manager.add_connector('source', mock_source)
        manager.add_connector('target1', mock_target1)
        manager.add_connector('target2', mock_target2)
        
        result = manager.sync_file_across_connectors(
            'file.txt',
            'source',
            ['target1', 'target2']
        )
        
        assert result['success'] is False  # Overall failure due to one failed upload
        assert result['results']['target1']['success'] is True
        assert result['results']['target2']['success'] is False


class TestConnectorManagerHelpers:
    """Test helper methods."""
    
    def test_get_connector_for_operation_with_name(self, manager, mock_connector):
        """Test getting connector by name for operation."""
        manager.add_connector('test', mock_connector)
        
        connector = manager._get_connector_for_operation('test')
        
        assert connector == mock_connector
    
    def test_get_connector_for_operation_active(self, manager, mock_connector):
        """Test getting active connector for operation."""
        manager.add_connector('test', mock_connector)
        
        connector = manager._get_connector_for_operation(None)
        
        assert connector == mock_connector
    
    def test_get_connector_for_operation_none(self, manager):
        """Test getting connector when none available."""
        connector = manager._get_connector_for_operation(None)
        
        assert connector is None
