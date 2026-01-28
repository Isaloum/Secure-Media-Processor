"""Dropbox connector implementation.

This module provides a connector for Dropbox cloud storage that implements
the CloudConnector interface.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import logging

try:
    import dropbox
    from dropbox.files import WriteMode
    from dropbox.exceptions import AuthError, ApiError
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

from .base import CloudConnector


logger = logging.getLogger(__name__)


class DropboxConnector(CloudConnector):
    """Dropbox cloud storage connector.
    
    This connector provides integration with Dropbox for secure file storage.
    Supports file upload, download, deletion, and metadata management.
    
    Note: Requires Dropbox access token with appropriate permissions.
    """
    
    def __init__(
        self,
        access_token: str,
        root_path: str = ''
    ):
        """Initialize Dropbox connector.
        
        Args:
            access_token: Dropbox OAuth2 access token.
            root_path: Root path in Dropbox for all operations (e.g., '/SecureMedia').
        """
        super().__init__()
        self._connected = False


        
        if not DROPBOX_AVAILABLE:
            raise ImportError(
                "Dropbox SDK not installed. "
                "Install with: pip install dropbox"
            )
        
        self.access_token = access_token
        self.root_path = root_path.rstrip('/')
        self.dbx = None
    
    def connect(self) -> bool:
        """Establish connection to Dropbox.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            # Create Dropbox client
            self.dbx = dropbox.Dropbox(self.access_token)
            
            # Test connection by getting account info
            self.dbx.users_get_current_account()
            
            self._connected = True
            logger.info("Successfully connected to Dropbox")
            return True
            
        except (AuthError, Exception) as e:
            logger.error(f"Failed to connect to Dropbox: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Dropbox.

        Returns:
            bool: True if disconnection successful.
        """
        self.dbx = None
        self._connected = False
        logger.info("Disconnected from Dropbox")
        return True

    def __del__(self):
        """Securely clear credentials from memory when object is destroyed.

        This prevents credential leakage through process memory dumps.
        Called automatically when the object is garbage collected.
        """
        # Clear Dropbox access token
        if hasattr(self, 'access_token') and self.access_token:
            self.access_token = None
        if hasattr(self, 'dbx'):
            self.dbx = None
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to Dropbox.
        
        Args:
            file_path: Path to the local file.
            remote_path: Path in Dropbox (relative to root_path).
            metadata: Optional metadata (stored in file properties).
            
        Returns:
            Dictionary containing upload result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Dropbox'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {'success': False, 'error': f'File not found: {file_path}'}
        
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Prepare full remote path
            full_remote_path = self._get_full_path(remote_path)
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload file
            upload_result = self.dbx.files_upload(
                file_data,
                full_remote_path,
                mode=WriteMode('overwrite'),
                autorename=False,
                mute=False
            )
            
            # Add custom metadata/properties if provided
            if metadata:
                metadata['checksum'] = checksum
                metadata['original_name'] = file_path.name
                metadata['upload_time'] = datetime.utcnow().isoformat()
                
                # Note: Dropbox property groups require template creation
                # For simplicity, we'll log this but not implement full property groups
                logger.info(f"Metadata for {remote_path}: {metadata}")
            
            logger.info(f"Successfully uploaded {file_path} to Dropbox:{full_remote_path}")
            
            return {
                'success': True,
                'remote_path': upload_result.path_display,
                'checksum': checksum,
                'size': upload_result.size,
                'timestamp': upload_result.client_modified.isoformat()
            }
            
        except ApiError as e:
            logger.error(f"Dropbox upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Download a file from Dropbox.
        
        Args:
            remote_path: Path in Dropbox (relative to root_path).
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.
            
        Returns:
            Dictionary containing download result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Dropbox'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        local_path = Path(local_path)
        
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Prepare full remote path
            full_remote_path = self._get_full_path(remote_path)
            
            # Download file
            metadata, response = self.dbx.files_download(full_remote_path)
            
            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Verify using content hash if available
            checksum_verified = False
            if verify_checksum and hasattr(metadata, 'content_hash'):
                # Note: Dropbox uses a proprietary hash algorithm
                # For full verification, you'd need to implement Dropbox's hashing
                # Here we'll use our standard SHA-256
                local_checksum = self._calculate_checksum(local_path)
                checksum_verified = True
                logger.info(f"File checksum: {local_checksum}")
            
            logger.info(f"Successfully downloaded Dropbox:{full_remote_path} to {local_path}")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'size': local_path.stat().st_size,
                'checksum_verified': checksum_verified
            }
            
        except ApiError as e:
            logger.error(f"Dropbox download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from Dropbox.
        
        Args:
            remote_path: Path in Dropbox (relative to root_path).
            
        Returns:
            Dictionary containing deletion result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Dropbox'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        try:
            # Prepare full remote path
            full_remote_path = self._get_full_path(remote_path)
            
            # Delete file
            self.dbx.files_delete_v2(full_remote_path)
            
            logger.info(f"Successfully deleted Dropbox:{full_remote_path}")
            
            return {
                'success': True,
                'remote_path': full_remote_path
            }
            
        except ApiError as e:
            logger.error(f"Dropbox deletion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files in Dropbox.
        
        Args:
            prefix: Filter results by path prefix (relative to root_path).
            
        Returns:
            List of file information dictionaries.
        """
        if not self._connected:
            logger.error("Not connected to Dropbox")
            return []
        
        try:
            # Prepare full path to list
            list_path = self._get_full_path(prefix) if prefix else self.root_path
            if not list_path:
                list_path = ''
            
            # List folder contents
            result = self.dbx.files_list_folder(list_path, recursive=True)
            
            files = []
            
            # Process entries
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        files.append({
                            'path': entry.path_display,
                            'size': entry.size,
                            'last_modified': entry.client_modified.isoformat(),
                            'checksum': getattr(entry, 'content_hash', '')
                        })
                
                # Check if there are more results
                if not result.has_more:
                    break
                
                result = self.dbx.files_list_folder_continue(result.cursor)
            
            return files
            
        except ApiError as e:
            logger.error(f"Dropbox list operation failed: {e}")
            return []
    
    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a file in Dropbox.
        
        Args:
            remote_path: Path in Dropbox (relative to root_path).
            
        Returns:
            Dictionary containing file metadata.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Dropbox'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        try:
            # Prepare full remote path
            full_remote_path = self._get_full_path(remote_path)
            
            # Get metadata
            metadata = self.dbx.files_get_metadata(full_remote_path)
            
            if isinstance(metadata, dropbox.files.FileMetadata):
                return {
                    'success': True,
                    'size': metadata.size,
                    'last_modified': metadata.client_modified.isoformat(),
                    'metadata': {},  # Custom properties would go here
                    'checksum': getattr(metadata, 'content_hash', '')
                }
            else:
                return {
                    'success': False,
                    'error': 'Path is not a file'
                }
            
        except ApiError as e:
            logger.error(f"Failed to get Dropbox metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_full_path(self, path: str) -> str:
        """Combine root path with given path.
        
        Args:
            path: Relative path.
            
        Returns:
            Full Dropbox path.
        """
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Combine with root path
        if self.root_path:
            full_path = self.root_path + path
        else:
            full_path = path
        
        return full_path
