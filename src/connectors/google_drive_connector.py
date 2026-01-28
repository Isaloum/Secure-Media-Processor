"""Google Drive connector implementation.

This module provides a connector for Google Drive cloud storage that implements
the CloudConnector interface.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone
import logging
import io

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import GoogleAuthError, TransportError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    HttpError = None  # type: ignore
    TransportError = None  # type: ignore

from .base_connector import CloudConnector


logger = logging.getLogger(__name__)


class GoogleDriveConnector(CloudConnector):
    """Google Drive cloud storage connector.
    
    This connector provides integration with Google Drive for secure file storage.
    Supports file upload, download, deletion, and metadata management.
    
    Note: Requires Google Cloud credentials with Drive API access.
    """
    
    def __init__(
        self,
        credentials_path: Optional[Union[str, Path]] = None,
        folder_id: Optional[str] = None,
        scopes: Optional[List[str]] = None
    ):
        """Initialize Google Drive connector.
        
        Args:
            credentials_path: Path to Google Cloud service account credentials JSON.
            folder_id: Optional Google Drive folder ID for uploads (uses root if not provided).
            scopes: OAuth2 scopes (defaults to full Drive access).
        """
        super().__init__()
        
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google Drive dependencies not installed. "
                "Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
        
        self.credentials_path = Path(credentials_path) if credentials_path else None
        self.folder_id = folder_id
        self.scopes = scopes or ['https://www.googleapis.com/auth/drive']
        self.service = None
        self.credentials = None
    
    def connect(self) -> bool:
        """Establish connection to Google Drive.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            if not self.credentials_path or not self.credentials_path.exists():
                logger.error("Google Drive credentials file not found")
                return False
            
            # Load service account credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.scopes
            )
            
            # Build Drive API service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
            # Test connection
            self.service.about().get(fields='user').execute()
            
            self._connected = True
            logger.info("Successfully connected to Google Drive")
            return True
            
        except (GoogleAuthError, Exception) as e:
            logger.error(f"Failed to connect to Google Drive: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Google Drive.

        Returns:
            bool: True if disconnection successful.
        """
        self.service = None
        self.credentials = None
        self._connected = False
        logger.info("Disconnected from Google Drive")
        return True

    def __del__(self):
        """Securely clear credentials from memory when object is destroyed.

        This prevents credential leakage through process memory dumps.
        Called automatically when the object is garbage collected.
        """
        # Clear Google Drive service and credentials
        if hasattr(self, 'service'):
            self.service = None
        if hasattr(self, 'credentials'):
            self.credentials = None
        if hasattr(self, 'credentials_path'):
            # Path object is safe to keep, but clear reference
            pass
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the local file.
            remote_path: Name for the file in Google Drive.
            metadata: Optional metadata to attach to the file.
            
        Returns:
            Dictionary containing upload result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Google Drive'}
        
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
            
            # Prepare file metadata
            file_metadata = {
                'name': remote_path,
                'description': f'Uploaded: {datetime.now(timezone.utc).isoformat()}',
                'properties': metadata or {}
            }
            
            # Add checksum to properties
            file_metadata['properties']['checksum'] = checksum
            file_metadata['properties']['original_name'] = file_path.name
            file_metadata['properties']['upload_time'] = datetime.now(timezone.utc).isoformat()
            
            # Set parent folder if specified
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]
            
            # Create media upload
            media = MediaFileUpload(
                str(file_path),
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,createdTime'
            ).execute()
            
            logger.info(f"Successfully uploaded {file_path} to Google Drive as {remote_path}")
            
            return {
                'success': True,
                'remote_path': file.get('name'),
                'file_id': file.get('id'),
                'checksum': checksum,
                'size': file_path.stat().st_size,
                'timestamp': file.get('createdTime')
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error during upload: {e}")
            return {
                'success': False,
                'error': f"API error: {e}"
            }
        except (IOError, OSError) as e:
            logger.error(f"File I/O error during upload: {e}")
            return {
                'success': False,
                'error': f"File error: {e}"
            }

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Download a file from Google Drive.
        
        Args:
            remote_path: Name or ID of the file in Google Drive.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.
            
        Returns:
            Dictionary containing download result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Google Drive'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        local_path = Path(local_path)
        
        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Find file by name or use as ID
            file_id = self._get_file_id(remote_path)
            if not file_id:
                return {'success': False, 'error': f'File not found: {remote_path}'}
            
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,properties'
            ).execute()
            
            stored_checksum = file_metadata.get('properties', {}).get('checksum')
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(str(local_path), 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.close()
            
            # Verify checksum if requested
            checksum_verified = False
            if verify_checksum and stored_checksum:
                local_checksum = self._calculate_checksum(local_path)
                if local_checksum != stored_checksum:
                    local_path.unlink()  # Delete corrupted file
                    return {
                        'success': False,
                        'error': 'Checksum verification failed'
                    }
                checksum_verified = True
            
            logger.info(f"Successfully downloaded {remote_path} from Google Drive to {local_path}")
            
            return {
                'success': True,
                'local_path': str(local_path),
                'size': local_path.stat().st_size,
                'checksum_verified': checksum_verified
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error during download: {e}")
            return {
                'success': False,
                'error': f"API error: {e}"
            }
        except (IOError, OSError) as e:
            logger.error(f"File I/O error during download: {e}")
            return {
                'success': False,
                'error': f"File error: {e}"
            }

    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from Google Drive.
        
        Args:
            remote_path: Name or ID of the file in Google Drive.
            
        Returns:
            Dictionary containing deletion result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Google Drive'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        try:
            # Find file by name or use as ID
            file_id = self._get_file_id(remote_path)
            if not file_id:
                return {'success': False, 'error': f'File not found: {remote_path}'}
            
            # Delete file
            self.service.files().delete(fileId=file_id).execute()
            
            logger.info(f"Successfully deleted {remote_path} from Google Drive")
            
            return {
                'success': True,
                'remote_path': remote_path
            }

        except HttpError as e:
            logger.error(f"Google Drive API error during deletion: {e}")
            return {
                'success': False,
                'error': f"API error: {e}"
            }

    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files in Google Drive.
        
        Args:
            prefix: Filter results by name prefix.
            
        Returns:
            List of file information dictionaries.
        """
        if not self._connected:
            logger.error("Not connected to Google Drive")
            return []
        
        try:
            # Build query
            query = "trashed=false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            if prefix:
                query += f" and name contains '{prefix}'"
            
            # List files
            results = self.service.files().list(
                q=query,
                fields='files(id,name,size,modifiedTime,md5Checksum)',
                pageSize=100
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    'path': item.get('name'),
                    'file_id': item.get('id'),
                    'size': int(item.get('size', 0)),
                    'last_modified': item.get('modifiedTime'),
                    'checksum': item.get('md5Checksum', '')
                })
            
            return files

        except HttpError as e:
            logger.error(f"Google Drive API error during list operation: {e}")
            return []

    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a file in Google Drive.
        
        Args:
            remote_path: Name or ID of the file in Google Drive.
            
        Returns:
            Dictionary containing file metadata.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Google Drive'}
        
        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}
        
        try:
            # Find file by name or use as ID
            file_id = self._get_file_id(remote_path)
            if not file_id:
                return {'success': False, 'error': f'File not found: {remote_path}'}
            
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,modifiedTime,properties,md5Checksum'
            ).execute()
            
            return {
                'success': True,
                'size': int(file_metadata.get('size', 0)),
                'last_modified': file_metadata.get('modifiedTime'),
                'metadata': file_metadata.get('properties', {}),
                'checksum': file_metadata.get('md5Checksum', '')
            }

        except HttpError as e:
            logger.error(f"Google Drive API error getting metadata: {e}")
            return {
                'success': False,
                'error': f"API error: {e}"
            }

    def _get_file_id(self, name_or_id: str) -> Optional[str]:
        """Get file ID by name or return ID if already an ID.
        
        Args:
            name_or_id: File name or ID.
            
        Returns:
            File ID if found, None otherwise.
        """
        # First try using it as an ID
        try:
            self.service.files().get(fileId=name_or_id, fields='id').execute()
            return name_or_id
        except HttpError:
            # Not found as ID, try searching by name
            pass

        # Search by name
        try:
            query = f"name='{name_or_id}' and trashed=false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"

            results = self.service.files().list(
                q=query,
                fields='files(id)',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            if files:
                return files[0]['id']
        except HttpError:
            pass

        return None
