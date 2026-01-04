"""Test suite for ConnectorManager."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.connectors.connector_manager import ConnectorManager
from src.connectors.base_connector import CloudConnector


class MockConnector(CloudConnector):
    """Mock cloud connector for testing."""
    
    def __init__(self, name='MockConnector', should_connect=True):
        super().__init__()
        self.provider_name = name
        self.should_connect = should_connect
        self.uploaded_files = []
        self.downloaded_files = []
        self.deleted_files = []
    
    def connect(self):
        if self.should_connect:
            self._connected = True
            return True
        return False
    
    def disconnect(self):
        self._connected = False
        return True
    
    def upload_file(self, file_path, remote_path, metadata=None):
        self.uploaded_files.append((file_path, remote_path, metadata))
        return {
            'success': True,
            'remote_path': remote_path,
            'checksum': 'mock_checksum',
            'size': 100,
            'timestamp': '2024-01-01T00:00:00Z'
        }
    
    def download_file(self, remote_path, local_path, verify_checksum=True):
        self.downloaded_files.append((remote_path, local_path, verify_checksum))
        # Create the file
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_text("mock content")
        return {
            'success': True,
            'local_path': str(local_path),
            'size': 100,
            'checksum_verified': verify_checksum
        }
    
    def delete_file(self, remote_path):
        self.deleted_files.append(remote_path)
        return {
            'success': True,
            'remote_path': remote_path
        }
    
    def list_files(self, prefix=''):
        return [
            {'path': f'{prefix}file1.txt', 'size': 100, 'last_modified': '2024-01-01'},
            {'path': f'{prefix}file2.txt', 'size': 200, 'last_modified': '2024-01-02'}
        ]
    
    def get_file_metadata(self, remote_path):
        return {
            'success': True,
            'size': 100,
            'last_modified': '2024-01-01',
            'metadata': {},
            'checksum': 'mock_checksum'
        }


@pytest.fixture
def manager():
    """Create a ConnectorManager instance."""
    return ConnectorManager()


@pytest.fixture
def mock_connector():
    """Create a mock connector."""
    return MockConnector(name='TestProvider')


def test_manager_initialization():
    """Test ConnectorManager initialization."""
    manager = ConnectorManager()
    
    assert len(manager.connectors) == 0
    assert manager.active_connector_name is None


def test_add_connector(manager, mock_connector):
    """Test adding a connector."""
    result = manager.add_connector('test', mock_connector)
    
    assert result is True
    assert 'test' in manager.connectors
    assert manager.active_connector_name == 'test'


def test_add_multiple_connectors(manager):
    """Test adding multiple connectors."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    assert len(manager.connectors) == 2
    assert manager.active_connector_name == 'conn1'  # First one is active


def test_add_connector_replace_existing(manager, mock_connector):
    """Test replacing an existing connector."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('test', connector1)
    manager.add_connector('test', connector2)  # Replace
    
    assert len(manager.connectors) == 1
    assert manager.connectors['test'] == connector2


def test_remove_connector(manager, mock_connector):
    """Test removing a connector."""
    manager.add_connector('test', mock_connector)
    
    result = manager.remove_connector('test')
    
    assert result is True
    assert 'test' not in manager.connectors
    assert manager.active_connector_name is None


def test_remove_nonexistent_connector(manager):
    """Test removing a connector that doesn't exist."""
    result = manager.remove_connector('nonexistent')
    
    assert result is False


def test_remove_active_connector(manager):
    """Test removing the active connector sets new active."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    manager.remove_connector('conn1')
    
    assert manager.active_connector_name == 'conn2'


def test_get_connector(manager, mock_connector):
    """Test getting a connector by name."""
    manager.add_connector('test', mock_connector)
    
    connector = manager.get_connector('test')
    
    assert connector == mock_connector


def test_get_nonexistent_connector(manager):
    """Test getting a connector that doesn't exist."""
    connector = manager.get_connector('nonexistent')
    
    assert connector is None


def test_set_active_connector(manager):
    """Test setting the active connector."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    result = manager.set_active('conn2')
    
    assert result is True
    assert manager.active_connector_name == 'conn2'


def test_set_active_nonexistent(manager):
    """Test setting active to a nonexistent connector."""
    result = manager.set_active('nonexistent')
    
    assert result is False


def test_get_active_connector(manager, mock_connector):
    """Test getting the active connector."""
    manager.add_connector('test', mock_connector)
    
    active = manager.get_active_connector()
    
    assert active == mock_connector


def test_get_active_connector_none(manager):
    """Test getting active connector when none set."""
    active = manager.get_active_connector()
    
    assert active is None


def test_list_connectors(manager):
    """Test listing all connectors."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    connectors = manager.list_connectors()
    
    assert len(connectors) == 2
    assert connectors[0]['name'] == 'conn1'
    assert connectors[0]['provider'] == 'Provider1'
    assert connectors[0]['active'] is True
    assert connectors[1]['active'] is False


def test_connect_all(manager):
    """Test connecting all connectors."""
    connector1 = MockConnector(name='Provider1', should_connect=True)
    connector2 = MockConnector(name='Provider2', should_connect=True)
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    results = manager.connect_all()
    
    assert results['conn1'] is True
    assert results['conn2'] is True
    assert connector1.is_connected()
    assert connector2.is_connected()


def test_connect_all_with_failure(manager):
    """Test connecting all when one fails."""
    connector1 = MockConnector(name='Provider1', should_connect=True)
    connector2 = MockConnector(name='Provider2', should_connect=False)
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    results = manager.connect_all()
    
    assert results['conn1'] is True
    assert results['conn2'] is False
    assert connector1.is_connected()
    assert not connector2.is_connected()


def test_disconnect_all(manager):
    """Test disconnecting all connectors."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    manager.connect_all()
    
    results = manager.disconnect_all()
    
    assert results['conn1'] is True
    assert results['conn2'] is True
    assert not connector1.is_connected()
    assert not connector2.is_connected()


def test_upload_file_with_active_connector(manager, mock_connector, tmp_path):
    """Test uploading file using active connector."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    manager.add_connector('test', mock_connector)
    
    result = manager.upload_file(test_file, 'remote/test.txt')
    
    assert result['success'] is True
    assert len(mock_connector.uploaded_files) == 1


def test_upload_file_with_specific_connector(manager, tmp_path):
    """Test uploading file using specific connector."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    
    manager.add_connector('conn1', connector1)
    manager.add_connector('conn2', connector2)
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = manager.upload_file(test_file, 'remote/test.txt', connector_name='conn2')
    
    assert result['success'] is True
    assert len(connector1.uploaded_files) == 0
    assert len(connector2.uploaded_files) == 1


def test_upload_file_no_connector(manager, tmp_path):
    """Test uploading file when no connector available."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = manager.upload_file(test_file, 'remote/test.txt')
    
    assert result['success'] is False
    assert 'No connector available' in result['error']


def test_download_file_with_active_connector(manager, mock_connector, tmp_path):
    """Test downloading file using active connector."""
    local_path = tmp_path / "downloaded.txt"
    
    manager.add_connector('test', mock_connector)
    
    result = manager.download_file('remote/test.txt', local_path)
    
    assert result['success'] is True
    assert len(mock_connector.downloaded_files) == 1
    assert local_path.exists()


def test_delete_file_with_active_connector(manager, mock_connector):
    """Test deleting file using active connector."""
    manager.add_connector('test', mock_connector)
    
    result = manager.delete_file('remote/test.txt')
    
    assert result['success'] is True
    assert len(mock_connector.deleted_files) == 1


def test_list_files_with_active_connector(manager, mock_connector):
    """Test listing files using active connector."""
    manager.add_connector('test', mock_connector)
    
    result = manager.list_files(prefix='docs/')
    
    assert len(result) == 2
    assert result[0]['path'] == 'docs/file1.txt'


def test_list_files_no_connector(manager):
    """Test listing files when no connector available."""
    result = manager.list_files()
    
    assert result == []


def test_get_file_metadata_with_active_connector(manager, mock_connector):
    """Test getting file metadata using active connector."""
    manager.add_connector('test', mock_connector)
    
    result = manager.get_file_metadata('remote/test.txt')
    
    assert result['success'] is True
    assert result['size'] == 100


def test_sync_file_across_connectors(manager, tmp_path):
    """Test syncing file across multiple connectors."""
    connector1 = MockConnector(name='Provider1')
    connector2 = MockConnector(name='Provider2')
    connector3 = MockConnector(name='Provider3')
    
    manager.add_connector('source', connector1)
    manager.add_connector('target1', connector2)
    manager.add_connector('target2', connector3)
    
    result = manager.sync_file_across_connectors(
        'file.txt',
        source_connector='source',
        target_connectors=['target1', 'target2']
    )
    
    assert result['success'] is True
    assert len(connector2.uploaded_files) == 1
    assert len(connector3.uploaded_files) == 1


def test_sync_file_source_not_found(manager):
    """Test syncing when source connector not found."""
    result = manager.sync_file_across_connectors(
        'file.txt',
        source_connector='nonexistent',
        target_connectors=['target']
    )
    
    assert result['success'] is False
    assert 'not found' in result['error']


def test_sync_file_target_not_found(manager):
    """Test syncing when target connector not found."""
    connector1 = MockConnector(name='Provider1')
    
    manager.add_connector('source', connector1)
    
    result = manager.sync_file_across_connectors(
        'file.txt',
        source_connector='source',
        target_connectors=['nonexistent']
    )
    
    assert result['success'] is False
    assert 'nonexistent' in result['results']
    assert result['results']['nonexistent']['success'] is False


def test_manager_repr(manager):
    """Test string representation of manager."""
    connector = MockConnector()
    manager.add_connector('test', connector)
    
    repr_str = repr(manager)
    
    assert 'ConnectorManager' in repr_str
    assert 'connectors=1' in repr_str
    assert "active='test'" in repr_str
