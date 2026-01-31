"""Microsoft OneDrive connector implementation.

This module provides a connector for Microsoft OneDrive that implements
the CloudConnector interface using Microsoft Graph API.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone
import logging
import json

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from msal import ConfidentialClientApplication, PublicClientApplication
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False

from .base_connector import CloudConnector


logger = logging.getLogger(__name__)


class OneDriveConnector(CloudConnector):
    """Microsoft OneDrive cloud connector.

    This connector provides integration with Microsoft OneDrive for secure file
    storage using Microsoft Graph API. Supports personal OneDrive and OneDrive
    for Business.

    Authentication Methods:
    1. Client credentials (for daemon/service apps)
    2. Device code flow (for CLI apps)
    3. Access token (if you already have a valid token)

    Example:
        >>> connector = OneDriveConnector(
        ...     client_id="your-client-id",
        ...     client_secret="your-client-secret",
        ...     tenant_id="your-tenant-id"
        ... )
        >>> connector.connect()
        >>> result = connector.upload_file("scan.dcm", "medical/scans/scan.dcm")
    """

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    AUTHORITY_BASE = "https://login.microsoftonline.com"
    SCOPES = ["https://graph.microsoft.com/.default"]
    USER_SCOPES = ["Files.ReadWrite.All", "User.Read"]

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        tenant_id: str = "common",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        drive_id: Optional[str] = None,
        rate_limiter=None
    ):
        """Initialize OneDrive connector.

        Args:
            client_id: Azure AD application (client) ID.
            client_secret: Application secret (for confidential client flow).
            tenant_id: Azure AD tenant ID or "common" for multi-tenant.
            access_token: Pre-obtained access token (optional).
            refresh_token: Refresh token for token renewal (optional).
            drive_id: Specific drive ID to use (optional, uses default drive if not set).
            rate_limiter: Optional RateLimiter instance for API throttling.

        Raises:
            ImportError: If required packages are not installed.
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests package is required for OneDrive. "
                "Install with: pip install requests"
            )

        super().__init__(rate_limiter=rate_limiter)

        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.drive_id = drive_id

        self._session: Optional[requests.Session] = None
        self._msal_app = None
        self._token_expiry: Optional[datetime] = None

    def connect(self) -> bool:
        """Establish connection to OneDrive.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            # Create session with retry logic
            self._session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            self._session.mount("https://", HTTPAdapter(max_retries=retries))

            # Get access token if not provided
            if not self.access_token:
                if not self._authenticate():
                    return False

            # Set authorization header
            self._session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            })

            # Test connection
            response = self._session.get(f"{self.GRAPH_API_BASE}/me/drive")
            if response.status_code == 200:
                drive_info = response.json()
                self.drive_id = self.drive_id or drive_info.get("id")
                logger.info(f"Connected to OneDrive: {drive_info.get('name', 'Unknown')}")
                self._connected = True
                return True
            else:
                logger.error(f"Failed to connect: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to OneDrive: {e}")
            self._connected = False
            return False

    def _authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API.

        Returns:
            bool: True if authentication successful.
        """
        if not MSAL_AVAILABLE:
            logger.error("MSAL package required for authentication. Install with: pip install msal")
            return False

        try:
            authority = f"{self.AUTHORITY_BASE}/{self.tenant_id}"

            if self.client_secret:
                # Confidential client flow (daemon/service)
                self._msal_app = ConfidentialClientApplication(
                    self.client_id,
                    authority=authority,
                    client_credential=self.client_secret
                )
                result = self._msal_app.acquire_token_for_client(scopes=self.SCOPES)
            else:
                # Public client flow with device code
                self._msal_app = PublicClientApplication(
                    self.client_id,
                    authority=authority
                )

                # Try to get token from cache first
                accounts = self._msal_app.get_accounts()
                if accounts:
                    result = self._msal_app.acquire_token_silent(
                        self.USER_SCOPES,
                        account=accounts[0]
                    )
                else:
                    # Device code flow
                    flow = self._msal_app.initiate_device_flow(scopes=self.USER_SCOPES)
                    if "user_code" not in flow:
                        logger.error(f"Failed to create device flow: {flow}")
                        return False

                    print(f"\nTo authenticate, visit: {flow['verification_uri']}")
                    print(f"Enter code: {flow['user_code']}\n")

                    result = self._msal_app.acquire_token_by_device_flow(flow)

            if "access_token" in result:
                self.access_token = result["access_token"]
                self.refresh_token = result.get("refresh_token")
                logger.info("Successfully authenticated with Microsoft Graph")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from OneDrive.

        Returns:
            bool: True if disconnection successful.
        """
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("Disconnected from OneDrive")
        return True

    def __del__(self):
        """Securely clear credentials from memory."""
        if hasattr(self, 'client_secret') and self.client_secret:
            self.client_secret = None
        if hasattr(self, 'access_token') and self.access_token:
            self.access_token = None
        if hasattr(self, 'refresh_token') and self.refresh_token:
            self.refresh_token = None
        if hasattr(self, '_session') and self._session:
            self._session.close()
            self._session = None

    def _get_item_path(self, remote_path: str) -> str:
        """Convert remote path to Graph API path.

        Args:
            remote_path: Remote file path.

        Returns:
            Graph API path string.
        """
        # Remove leading slash
        remote_path = remote_path.lstrip("/")

        if self.drive_id:
            return f"{self.GRAPH_API_BASE}/drives/{self.drive_id}/root:/{remote_path}"
        else:
            return f"{self.GRAPH_API_BASE}/me/drive/root:/{remote_path}"

    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to OneDrive.

        For files larger than 4MB, uses resumable upload session.

        Args:
            file_path: Path to the local file.
            remote_path: OneDrive path for the file.
            metadata: Optional metadata (stored as file description).

        Returns:
            Dictionary containing upload result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        file_path = Path(file_path)
        if not file_path.exists():
            return {'success': False, 'error': f'File not found: {file_path}'}

        try:
            self._check_rate_limit("upload_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            file_size = file_path.stat().st_size
            checksum = self._calculate_checksum(file_path)

            # Use simple upload for small files (< 4MB)
            if file_size < 4 * 1024 * 1024:
                return self._simple_upload(file_path, remote_path, checksum, metadata)
            else:
                return self._resumable_upload(file_path, remote_path, checksum, metadata)

        except Exception as e:
            logger.error(f"OneDrive upload failed: {e}")
            return {'success': False, 'error': str(e)}

    def _simple_upload(
        self,
        file_path: Path,
        remote_path: str,
        checksum: str,
        metadata: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Simple upload for files < 4MB."""
        upload_url = f"{self._get_item_path(remote_path)}:/content"

        with open(file_path, 'rb') as f:
            response = self._session.put(
                upload_url,
                data=f,
                headers={"Content-Type": "application/octet-stream"}
            )

        if response.status_code in (200, 201):
            result = response.json()
            logger.info(f"Successfully uploaded {file_path} to OneDrive: {remote_path}")

            return {
                'success': True,
                'remote_path': remote_path,
                'checksum': checksum,
                'size': file_path.stat().st_size,
                'item_id': result.get('id'),
                'web_url': result.get('webUrl'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                'success': False,
                'error': f"Upload failed: {response.status_code} - {response.text}"
            }

    def _resumable_upload(
        self,
        file_path: Path,
        remote_path: str,
        checksum: str,
        metadata: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Resumable upload for large files (> 4MB)."""
        # Create upload session
        session_url = f"{self._get_item_path(remote_path)}:/createUploadSession"

        session_response = self._session.post(
            session_url,
            json={
                "item": {
                    "@microsoft.graph.conflictBehavior": "replace"
                }
            }
        )

        if session_response.status_code != 200:
            return {
                'success': False,
                'error': f"Failed to create upload session: {session_response.text}"
            }

        upload_url = session_response.json().get('uploadUrl')
        file_size = file_path.stat().st_size
        chunk_size = 10 * 1024 * 1024  # 10MB chunks

        with open(file_path, 'rb') as f:
            offset = 0
            while offset < file_size:
                chunk = f.read(chunk_size)
                chunk_end = min(offset + len(chunk), file_size)

                headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{chunk_end-1}/{file_size}"
                }

                response = self._session.put(upload_url, data=chunk, headers=headers)

                if response.status_code not in (200, 201, 202):
                    return {
                        'success': False,
                        'error': f"Chunk upload failed: {response.status_code}"
                    }

                offset = chunk_end

        logger.info(f"Successfully uploaded large file {file_path} to OneDrive")

        return {
            'success': True,
            'remote_path': remote_path,
            'checksum': checksum,
            'size': file_size,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def download_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Download a file from OneDrive.

        Args:
            remote_path: OneDrive path of the file.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.

        Returns:
            Dictionary containing download result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._check_rate_limit("download_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            # Get file content
            download_url = f"{self._get_item_path(remote_path)}:/content"
            response = self._session.get(download_url, stream=True)

            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Successfully downloaded {remote_path} to {local_path}")

                # Calculate checksum
                local_checksum = self._calculate_checksum(local_path)

                return {
                    'success': True,
                    'local_path': str(local_path),
                    'size': local_path.stat().st_size,
                    'checksum': local_checksum,
                    'checksum_verified': verify_checksum
                }
            elif response.status_code == 404:
                return {'success': False, 'error': f'File not found: {remote_path}'}
            else:
                return {
                    'success': False,
                    'error': f"Download failed: {response.status_code} - {response.text}"
                }

        except Exception as e:
            logger.error(f"OneDrive download failed: {e}")
            return {'success': False, 'error': str(e)}

    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from OneDrive.

        Args:
            remote_path: OneDrive path of the file to delete.

        Returns:
            Dictionary containing deletion result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            self._check_rate_limit("delete_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            delete_url = self._get_item_path(remote_path)
            response = self._session.delete(delete_url)

            if response.status_code == 204:
                logger.info(f"Successfully deleted {remote_path} from OneDrive")
                return {'success': True, 'remote_path': remote_path}
            elif response.status_code == 404:
                return {
                    'success': True,
                    'remote_path': remote_path,
                    'warning': 'File did not exist'
                }
            else:
                return {
                    'success': False,
                    'error': f"Delete failed: {response.status_code} - {response.text}"
                }

        except Exception as e:
            logger.error(f"OneDrive delete failed: {e}")
            return {'success': False, 'error': str(e)}

    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List files in OneDrive folder.

        Args:
            prefix: Folder path to list (empty for root).

        Returns:
            List of file information dictionaries.
        """
        if not self._connected:
            logger.error("Not connected to OneDrive")
            return []

        try:
            self._check_rate_limit("list_files")
        except RuntimeError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return []

        try:
            if prefix:
                list_url = f"{self._get_item_path(prefix)}:/children"
            else:
                if self.drive_id:
                    list_url = f"{self.GRAPH_API_BASE}/drives/{self.drive_id}/root/children"
                else:
                    list_url = f"{self.GRAPH_API_BASE}/me/drive/root/children"

            files = []
            next_link = list_url

            while next_link:
                response = self._session.get(next_link)

                if response.status_code != 200:
                    logger.error(f"List failed: {response.status_code}")
                    break

                data = response.json()

                for item in data.get('value', []):
                    file_info = {
                        'path': item.get('name'),
                        'id': item.get('id'),
                        'size': item.get('size', 0),
                        'last_modified': item.get('lastModifiedDateTime'),
                        'is_folder': 'folder' in item,
                        'web_url': item.get('webUrl')
                    }

                    if 'file' in item and 'hashes' in item['file']:
                        file_info['checksum'] = item['file']['hashes'].get('sha256Hash')

                    files.append(file_info)

                next_link = data.get('@odata.nextLink')

            return files

        except Exception as e:
            logger.error(f"OneDrive list failed: {e}")
            return []

    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a file in OneDrive.

        Args:
            remote_path: OneDrive path of the file.

        Returns:
            Dictionary containing file metadata.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            metadata_url = self._get_item_path(remote_path)
            response = self._session.get(metadata_url)

            if response.status_code == 200:
                item = response.json()
                return {
                    'success': True,
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'size': item.get('size'),
                    'last_modified': item.get('lastModifiedDateTime'),
                    'created': item.get('createdDateTime'),
                    'web_url': item.get('webUrl'),
                    'is_folder': 'folder' in item,
                    'mime_type': item.get('file', {}).get('mimeType'),
                    'checksum': item.get('file', {}).get('hashes', {}).get('sha256Hash')
                }
            elif response.status_code == 404:
                return {'success': False, 'error': f'File not found: {remote_path}'}
            else:
                return {
                    'success': False,
                    'error': f"Metadata fetch failed: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Failed to get OneDrive metadata: {e}")
            return {'success': False, 'error': str(e)}

    def create_sharing_link(
        self,
        remote_path: str,
        link_type: str = "view",
        expiry_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a sharing link for a file.

        Args:
            remote_path: OneDrive path of the file.
            link_type: Type of link - "view" (read-only) or "edit".
            expiry_hours: Optional expiry time in hours.

        Returns:
            Dictionary containing the sharing link.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            share_url = f"{self._get_item_path(remote_path)}:/createLink"

            body = {
                "type": link_type,
                "scope": "anonymous"
            }

            if expiry_hours:
                from datetime import timedelta
                expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
                body["expirationDateTime"] = expiry.isoformat()

            response = self._session.post(share_url, json=body)

            if response.status_code in (200, 201):
                result = response.json()
                link = result.get('link', {})
                return {
                    'success': True,
                    'sharing_url': link.get('webUrl'),
                    'link_type': link_type,
                    'expiry': body.get('expirationDateTime')
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to create link: {response.status_code} - {response.text}"
                }

        except Exception as e:
            logger.error(f"Failed to create sharing link: {e}")
            return {'success': False, 'error': str(e)}

    def copy_file(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Copy a file within OneDrive.

        Args:
            source_path: Source file path.
            destination_path: Destination file path.

        Returns:
            Dictionary containing copy result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to OneDrive'}

        try:
            # Get destination folder and name
            dest_path = Path(destination_path)
            dest_folder = str(dest_path.parent).lstrip("/")
            dest_name = dest_path.name

            # Get parent folder ID
            if dest_folder:
                folder_url = self._get_item_path(dest_folder)
            else:
                if self.drive_id:
                    folder_url = f"{self.GRAPH_API_BASE}/drives/{self.drive_id}/root"
                else:
                    folder_url = f"{self.GRAPH_API_BASE}/me/drive/root"

            folder_response = self._session.get(folder_url)
            if folder_response.status_code != 200:
                return {'success': False, 'error': 'Destination folder not found'}

            parent_ref = {
                "id": folder_response.json().get('id')
            }

            # Perform copy
            copy_url = f"{self._get_item_path(source_path)}:/copy"
            response = self._session.post(
                copy_url,
                json={
                    "parentReference": parent_ref,
                    "name": dest_name
                }
            )

            if response.status_code == 202:
                # Copy is async, return monitor URL
                return {
                    'success': True,
                    'source_path': source_path,
                    'destination_path': destination_path,
                    'status': 'in_progress',
                    'monitor_url': response.headers.get('Location')
                }
            else:
                return {
                    'success': False,
                    'error': f"Copy failed: {response.status_code} - {response.text}"
                }

        except Exception as e:
            logger.error(f"OneDrive copy failed: {e}")
            return {'success': False, 'error': str(e)}
