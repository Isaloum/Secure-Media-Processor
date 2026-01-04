"""Base connector interface for cloud storage providers.

This module defines the abstract base class that all cloud storage connectors
must implement. This ensures a consistent API across different cloud providers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


class CloudConnector(ABC):
    """Abstract base class for cloud storage connectors.
    
    All cloud storage implementations (S3, Google Drive, Dropbox, etc.)
    must inherit from this class and implement all abstract methods.
    """
    
    def __init__(self, **kwargs):
        """Initialize the cloud connector.
        
        Args:
            **kwargs: Provider-specific configuration parameters.
        """
        self.provider_name = self.__class__.__name__.replace('Connector', '')
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the cloud storage provider.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the cloud storage provider.
        
        Returns:
            bool: True if disconnection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to cloud storage.
        
        Args:
            file_path: Path to the local file.
            remote_path: Remote path/key where file will be stored.
            metadata: Optional metadata to attach to the file.
            
        Returns:
            Dictionary containing upload result information:
                - success (bool): Whether upload succeeded
                - remote_path (str): Remote path of uploaded file
                - size (int): File size in bytes
                - checksum (str): File checksum
                - timestamp (str): Upload timestamp
                - error (str, optional): Error message if failed
        """
        pass
    
    @abstractmethod
    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Download a file from cloud storage.
        
        Args:
            remote_path: Remote path/key of the file.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.
            
        Returns:
            Dictionary containing download result information:
                - success (bool): Whether download succeeded
                - local_path (str): Local path of downloaded file
                - size (int): File size in bytes
                - checksum_verified (bool): Whether checksum was verified
                - error (str, optional): Error message if failed
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from cloud storage.
        
        Args:
            remote_path: Remote path/key of the file to delete.
            
        Returns:
            Dictionary containing deletion result:
                - success (bool): Whether deletion succeeded
                - remote_path (str): Path of deleted file
                - error (str, optional): Error message if failed
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files in cloud storage.
        
        Args:
            prefix: Filter results by path prefix.
            
        Returns:
            List of dictionaries containing file information:
                - path (str): File path
                - size (int): File size in bytes
                - last_modified (str): Last modification timestamp
                - checksum (str, optional): File checksum
        """
        pass
    
    @abstractmethod
    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a file in cloud storage.
        
        Args:
            remote_path: Remote path/key of the file.
            
        Returns:
            Dictionary containing file metadata:
                - success (bool): Whether operation succeeded
                - size (int): File size in bytes
                - last_modified (str): Last modification timestamp
                - metadata (dict): Custom metadata
                - checksum (str, optional): File checksum
                - error (str, optional): Error message if failed
        """
        pass
    
    def is_connected(self) -> bool:
        """Check if connector is currently connected.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected
    
    def get_provider_name(self) -> str:
        """Get the name of the cloud storage provider.
        
        Returns:
            str: Provider name (e.g., 'S3', 'GoogleDrive', 'Dropbox').
        """
        return self.provider_name
    
    def _calculate_checksum(self, file_path: Union[str, Path]) -> str:
        """Calculate SHA-256 checksum of a file.
        
        This is a helper method that can be used by all connectors.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            str: Hexadecimal checksum string.
        """
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def __repr__(self) -> str:
        """String representation of the connector.
        
        Returns:
            str: Connector description.
        """
        status = "connected" if self._connected else "disconnected"
        return f"{self.provider_name}Connector({status})"
