"""Connector manager for plug-and-play cloud storage access.

This module provides a unified interface to manage multiple cloud storage
connectors. It enables easy switching between different providers and
supports multiple simultaneous connections.
"""

from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import logging

from .base import CloudConnector
from .s3 import S3Connector
from .google_drive import GoogleDriveConnector
from .dropbox import DropboxConnector


logger = logging.getLogger(__name__)


class ConnectorManager:
    """Manage multiple cloud storage connectors.
    
    This class provides a centralized way to:
    - Register and manage multiple cloud connectors
    - Switch between different cloud providers
    - Perform operations across multiple clouds
    - Maintain connections to various storage providers
    
    Example:
        >>> manager = ConnectorManager()
        >>> 
        >>> # Add S3 connector
        >>> manager.add_connector('s3', S3Connector(
        ...     bucket_name='my-bucket',
        ...     region='us-east-1'
        ... ))
        >>> 
        >>> # Add Dropbox connector
        >>> manager.add_connector('dropbox', DropboxConnector(
        ...     access_token='your-token'
        ... ))
        >>> 
        >>> # Use a specific connector
        >>> manager.set_active('s3')
        >>> manager.upload_file('file.txt', 'remote/file.txt')
        >>> 
        >>> # Or use connectors directly
        >>> manager.get_connector('dropbox').upload_file('file.txt', 'file.txt')
    """
    
    def __init__(self):
        """Initialize the connector manager."""
        self.connectors: Dict[str, CloudConnector] = {}
        self.active_connector_name: Optional[str] = None
    
    def add_connector(self, name: str, connector: CloudConnector) -> bool:
        """Add a cloud connector to the manager.
        
        Args:
            name: Unique name for this connector (e.g., 's3', 'gdrive', 'dropbox').
            connector: CloudConnector instance.
            
        Returns:
            bool: True if connector added successfully.
        """
        if name in self.connectors:
            logger.warning(f"Connector '{name}' already exists, replacing it")
        
        self.connectors[name] = connector
        logger.info(f"Added connector: {name} ({connector.get_provider_name()})")
        
        # Set as active if it's the first connector
        if not self.active_connector_name:
            self.active_connector_name = name
        
        return True
    
    def remove_connector(self, name: str) -> bool:
        """Remove a connector from the manager.
        
        Args:
            name: Name of the connector to remove.
            
        Returns:
            bool: True if connector removed successfully.
        """
        if name not in self.connectors:
            logger.error(f"Connector '{name}' not found")
            return False
        
        # Disconnect if connected
        connector = self.connectors[name]
        if connector.is_connected():
            connector.disconnect()
        
        del self.connectors[name]
        logger.info(f"Removed connector: {name}")
        
        # Clear active if it was the active connector
        if self.active_connector_name == name:
            self.active_connector_name = None
            # Set to first available connector if any
            if self.connectors:
                self.active_connector_name = next(iter(self.connectors))
        
        return True
    
    def get_connector(self, name: str) -> Optional[CloudConnector]:
        """Get a specific connector by name.
        
        Args:
            name: Name of the connector.
            
        Returns:
            CloudConnector instance or None if not found.
        """
        connector = self.connectors.get(name)
        if not connector:
            logger.error(f"Connector '{name}' not found")
        return connector
    
    def set_active(self, name: str) -> bool:
        """Set the active connector.
        
        Args:
            name: Name of the connector to set as active.
            
        Returns:
            bool: True if successful.
        """
        if name not in self.connectors:
            logger.error(f"Connector '{name}' not found")
            return False
        
        self.active_connector_name = name
        logger.info(f"Set active connector: {name}")
        return True
    
    def get_active_connector(self) -> Optional[CloudConnector]:
        """Get the currently active connector.
        
        Returns:
            CloudConnector instance or None if no active connector.
        """
        if not self.active_connector_name:
            logger.error("No active connector set")
            return None
        
        return self.connectors.get(self.active_connector_name)
    
    def list_connectors(self) -> List[Dict[str, str]]:
        """List all registered connectors.
        
        Returns:
            List of connector information dictionaries.
        """
        connectors_info = []
        for name, connector in self.connectors.items():
            connectors_info.append({
                'name': name,
                'provider': connector.get_provider_name(),
                'connected': connector.is_connected(),
                'active': name == self.active_connector_name
            })
        return connectors_info
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect all registered connectors.
        
        Returns:
            Dictionary mapping connector names to connection success status.
        """
        results = {}
        for name, connector in self.connectors.items():
            if not connector.is_connected():
                results[name] = connector.connect()
            else:
                results[name] = True
        return results
    
    def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect all connected connectors.
        
        Returns:
            Dictionary mapping connector names to disconnection success status.
        """
        results = {}
        for name, connector in self.connectors.items():
            if connector.is_connected():
                results[name] = connector.disconnect()
            else:
                results[name] = True
        return results
    
    # Convenience methods that operate on the active connector
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None,
        connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file using the active or specified connector.
        
        Args:
            file_path: Path to the local file.
            remote_path: Remote path for the file.
            metadata: Optional metadata.
            connector_name: Optional specific connector to use.
            
        Returns:
            Upload result dictionary.
        """
        connector = self._get_connector_for_operation(connector_name)
        if not connector:
            return {'success': False, 'error': 'No connector available'}
        
        return connector.upload_file(file_path, remote_path, metadata)
    
    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True,
        connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download a file using the active or specified connector.
        
        Args:
            remote_path: Remote path of the file.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify integrity.
            connector_name: Optional specific connector to use.
            
        Returns:
            Download result dictionary.
        """
        connector = self._get_connector_for_operation(connector_name)
        if not connector:
            return {'success': False, 'error': 'No connector available'}
        
        return connector.download_file(remote_path, local_path, verify_checksum)
    
    def delete_file(
        self,
        remote_path: str,
        connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a file using the active or specified connector.
        
        Args:
            remote_path: Remote path of the file to delete.
            connector_name: Optional specific connector to use.
            
        Returns:
            Deletion result dictionary.
        """
        connector = self._get_connector_for_operation(connector_name)
        if not connector:
            return {'success': False, 'error': 'No connector available'}
        
        return connector.delete_file(remote_path)
    
    def list_files(
        self,
        prefix: str = '',
        connector_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files using the active or specified connector.
        
        Args:
            prefix: Path prefix filter.
            connector_name: Optional specific connector to use.
            
        Returns:
            List of file information dictionaries.
        """
        connector = self._get_connector_for_operation(connector_name)
        if not connector:
            return []
        
        return connector.list_files(prefix)
    
    def get_file_metadata(
        self,
        remote_path: str,
        connector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get file metadata using the active or specified connector.
        
        Args:
            remote_path: Remote path of the file.
            connector_name: Optional specific connector to use.
            
        Returns:
            Metadata dictionary.
        """
        connector = self._get_connector_for_operation(connector_name)
        if not connector:
            return {'success': False, 'error': 'No connector available'}
        
        return connector.get_file_metadata(remote_path)
    
    def sync_file_across_connectors(
        self,
        remote_path: str,
        source_connector: str,
        target_connectors: List[str]
    ) -> Dict[str, Any]:
        """Sync a file from one cloud to multiple other clouds.
        
        This is useful for creating backups across multiple cloud providers.
        
        Args:
            remote_path: Path of the file in source connector.
            source_connector: Name of source connector.
            target_connectors: List of target connector names.
            
        Returns:
            Dictionary with sync results for each target.
        """
        import tempfile
        import os

        source = self.get_connector(source_connector)
        if not source:
            return {'success': False, 'error': f'Source connector {source_connector} not found'}

        results = {}

        # Create secure temporary file with restricted permissions (0600 - owner only)
        # This prevents other users on shared systems from reading the file
        fd = None
        tmp_path = None

        try:
            # Create temp file with secure permissions
            fd = tempfile.mkstemp(prefix='secure_media_', suffix='.tmp')
            tmp_path = Path(fd[1])  # fd is (file_descriptor, path) tuple

            # Set restrictive permissions (owner read/write only)
            os.chmod(tmp_path, 0o600)

            # Close file descriptor as we'll use the path directly
            os.close(fd[0])
            fd = None

            # Download from source to temporary file
            download_result = source.download_file(remote_path, tmp_path)
            if not download_result['success']:
                return {'success': False, 'error': 'Failed to download from source', 'details': download_result}

            # Upload to each target
            for target_name in target_connectors:
                target = self.get_connector(target_name)
                if not target:
                    results[target_name] = {'success': False, 'error': 'Connector not found'}
                    continue

                upload_result = target.upload_file(tmp_path, remote_path)
                results[target_name] = upload_result

        finally:
            # Secure cleanup: Overwrite file contents before deletion
            if tmp_path and tmp_path.exists():
                try:
                    # Overwrite with zeros before deletion (3-pass secure delete)
                    file_size = tmp_path.stat().st_size
                    with open(tmp_path, 'wb') as f:
                        # Pass 1: Write zeros
                        f.write(b'\0' * file_size)
                        f.flush()
                        os.fsync(f.fileno())
                        # Pass 2: Write ones
                        f.seek(0)
                        f.write(b'\xff' * file_size)
                        f.flush()
                        os.fsync(f.fileno())
                        # Pass 3: Write random data
                        f.seek(0)
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())
                    # Now delete
                    tmp_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to securely delete temp file: {e}")
                    # Try regular delete as fallback
                    try:
                        tmp_path.unlink()
                    except:
                        pass

            # Close file descriptor if still open
            if fd is not None:
                try:
                    os.close(fd)
                except:
                    pass
        
        return {
            'success': all(r.get('success', False) for r in results.values()),
            'results': results
        }
    
    def _get_connector_for_operation(self, connector_name: Optional[str]) -> Optional[CloudConnector]:
        """Get the connector to use for an operation.
        
        Args:
            connector_name: Specific connector name or None for active.
            
        Returns:
            CloudConnector instance or None.
        """
        if connector_name:
            return self.get_connector(connector_name)
        return self.get_active_connector()
    
    def __repr__(self) -> str:
        """String representation of the manager.
        
        Returns:
            Manager description.
        """
        active = self.active_connector_name or 'None'
        return f"ConnectorManager(connectors={len(self.connectors)}, active='{active}')"
