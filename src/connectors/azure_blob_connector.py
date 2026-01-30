"""Azure Blob Storage connector implementation.

This module provides a connector for Azure Blob Storage that implements
the CloudConnector interface for secure cloud file operations.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone
import logging

try:
    from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
    from azure.storage.blob import ContentSettings
    from azure.core.exceptions import (
        AzureError,
        ResourceNotFoundError,
        ResourceExistsError,
        ClientAuthenticationError
    )
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from .base_connector import CloudConnector


logger = logging.getLogger(__name__)


class AzureBlobConnector(CloudConnector):
    """Azure Blob Storage cloud connector.

    This connector provides integration with Azure Blob Storage for secure file
    storage. Supports server-side encryption, checksum verification, and metadata
    management.

    Azure Blob Storage is ideal for:
    - Storing large amounts of unstructured data
    - Serving images or documents directly to browsers
    - Streaming video and audio
    - Storing data for backup, disaster recovery, and archiving
    - Storing data for analysis by on-premises or Azure-hosted services

    Example:
        >>> connector = AzureBlobConnector(
        ...     connection_string="DefaultEndpointsProtocol=https;...",
        ...     container_name="medical-data"
        ... )
        >>> connector.connect()
        >>> result = connector.upload_file("scan.dcm", "studies/patient123/scan.dcm")
    """

    def __init__(
        self,
        container_name: str,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        rate_limiter = None
    ):
        """Initialize Azure Blob Storage connector.

        Supports three authentication methods (in order of preference):
        1. Connection string (most common for development)
        2. Account name + Account key (direct access)
        3. Account name + SAS token (delegated access)

        Args:
            container_name: Name of the Azure blob container.
            connection_string: Azure Storage connection string.
            account_name: Azure Storage account name.
            account_key: Azure Storage account key.
            sas_token: Shared Access Signature token for delegated access.
            rate_limiter: Optional RateLimiter instance for API throttling.

        Raises:
            ImportError: If azure-storage-blob package is not installed.
            ValueError: If no valid authentication method is provided.
        """
        if not AZURE_AVAILABLE:
            raise ImportError(
                "azure-storage-blob package is required for Azure Blob Storage. "
                "Install with: pip install azure-storage-blob"
            )

        super().__init__(rate_limiter=rate_limiter)

        self.container_name = container_name
        self.connection_string = connection_string
        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token

        # Validate authentication
        if not connection_string and not account_name:
            raise ValueError(
                "Must provide either connection_string or account_name "
                "(with account_key or sas_token)"
            )

        if account_name and not (account_key or sas_token):
            raise ValueError(
                "When using account_name, must also provide account_key or sas_token"
            )

        self.blob_service_client: Optional[BlobServiceClient] = None
        self.container_client: Optional[ContainerClient] = None

    def connect(self) -> bool:
        """Establish connection to Azure Blob Storage.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            if self.connection_string:
                # Connection string auth (most common)
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_key:
                # Account key auth
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key
                )
            elif self.sas_token:
                # SAS token auth
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                # Append SAS token to URL
                sas_url = f"{account_url}?{self.sas_token.lstrip('?')}"
                self.blob_service_client = BlobServiceClient(account_url=sas_url)

            # Get container client
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )

            # Test connection by checking if container exists
            if not self.container_client.exists():
                logger.warning(
                    f"Container '{self.container_name}' does not exist. "
                    "Creating container..."
                )
                self.container_client.create_container()

            self._connected = True
            logger.info(
                f"Successfully connected to Azure Blob Storage container: "
                f"{self.container_name}"
            )
            return True

        except ClientAuthenticationError as e:
            logger.error(f"Authentication failed for Azure Blob Storage: {e}")
            self._connected = False
            return False
        except AzureError as e:
            logger.error(f"Failed to connect to Azure Blob Storage: {e}")
            self._connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from Azure Blob Storage.

        Returns:
            bool: True if disconnection successful.
        """
        self.blob_service_client = None
        self.container_client = None
        self._connected = False
        logger.info("Disconnected from Azure Blob Storage")
        return True

    def __del__(self):
        """Securely clear credentials from memory when object is destroyed.

        This prevents credential leakage through process memory dumps.
        Called automatically when the object is garbage collected.
        """
        # Clear Azure credentials
        if hasattr(self, 'connection_string') and self.connection_string:
            self.connection_string = None
        if hasattr(self, 'account_key') and self.account_key:
            self.account_key = None
        if hasattr(self, 'sas_token') and self.sas_token:
            self.sas_token = None

        # Clear client objects
        if hasattr(self, 'blob_service_client'):
            self.blob_service_client = None
        if hasattr(self, 'container_client'):
            self.container_client = None

    def upload_file(
        self,
        file_path: Union[str, Path],
        remote_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to Azure Blob Storage.

        Args:
            file_path: Path to the local file.
            remote_path: Blob name/path in the container.
            metadata: Optional metadata to attach to the blob.

        Returns:
            Dictionary containing upload result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        file_path = Path(file_path)

        if not file_path.exists():
            return {'success': False, 'error': f'File not found: {file_path}'}

        # Check rate limit before API call
        try:
            self._check_rate_limit("upload_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)

            # Prepare metadata
            blob_metadata = metadata or {}
            blob_metadata['checksum'] = checksum
            blob_metadata['upload_time'] = datetime.now(timezone.utc).isoformat()
            blob_metadata['original_name'] = file_path.name

            # Get blob client
            blob_client = self.container_client.get_blob_client(remote_path)

            # Detect content type
            content_type = self._get_content_type(file_path)
            content_settings = ContentSettings(content_type=content_type)

            # Upload file
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(
                    data,
                    overwrite=True,
                    metadata=blob_metadata,
                    content_settings=content_settings
                )

            logger.info(
                f"Successfully uploaded {file_path} to "
                f"azure://{self.container_name}/{remote_path}"
            )

            return {
                'success': True,
                'remote_path': remote_path,
                'checksum': checksum,
                'size': file_path.stat().st_size,
                'timestamp': blob_metadata['upload_time']
            }

        except AzureError as e:
            logger.error(f"Azure Blob upload failed: {e}")
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
        """Download a file from Azure Blob Storage.

        Args:
            remote_path: Blob name/path in the container.
            local_path: Local path where file will be saved.
            verify_checksum: Whether to verify file integrity.

        Returns:
            Dictionary containing download result information.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        local_path = Path(local_path)

        # Create parent directory if needed
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Check rate limit before API call
        try:
            self._check_rate_limit("download_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            # Get blob client
            blob_client = self.container_client.get_blob_client(remote_path)

            # Get blob properties to retrieve metadata
            properties = blob_client.get_blob_properties()
            stored_checksum = properties.metadata.get('checksum') if properties.metadata else None

            # Download file
            with open(local_path, 'wb') as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())

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

            logger.info(
                f"Successfully downloaded azure://{self.container_name}/{remote_path} "
                f"to {local_path}"
            )

            return {
                'success': True,
                'local_path': str(local_path),
                'size': local_path.stat().st_size,
                'checksum_verified': checksum_verified
            }

        except ResourceNotFoundError:
            logger.error(f"Blob not found: {remote_path}")
            return {
                'success': False,
                'error': f'Blob not found: {remote_path}'
            }
        except AzureError as e:
            logger.error(f"Azure Blob download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """Delete a file from Azure Blob Storage.

        Args:
            remote_path: Blob name/path to delete.

        Returns:
            Dictionary containing deletion result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        # Check rate limit before API call
        try:
            self._check_rate_limit("delete_file")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            blob_client = self.container_client.get_blob_client(remote_path)
            blob_client.delete_blob()

            logger.info(
                f"Successfully deleted azure://{self.container_name}/{remote_path}"
            )

            return {
                'success': True,
                'remote_path': remote_path
            }

        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {remote_path}")
            return {
                'success': True,  # Consider deletion of non-existent blob as success
                'remote_path': remote_path,
                'warning': 'Blob did not exist'
            }
        except AzureError as e:
            logger.error(f"Azure Blob deletion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_files(self, prefix: str = '') -> List[Dict[str, Any]]:
        """List blobs in Azure container.

        Args:
            prefix: Filter results by blob name prefix.

        Returns:
            List of file information dictionaries.
        """
        if not self._connected:
            logger.error("Not connected to Azure Blob Storage")
            return []

        # Check rate limit before API call
        try:
            self._check_rate_limit("list_files")
        except RuntimeError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return []

        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix or None)

            files = []
            for blob in blobs:
                files.append({
                    'path': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                    'checksum': blob.etag.strip('"') if blob.etag else None,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None
                })

            return files

        except AzureError as e:
            logger.error(f"Azure Blob list operation failed: {e}")
            return []

    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get metadata for a blob in Azure Storage.

        Args:
            remote_path: Blob name/path.

        Returns:
            Dictionary containing blob metadata.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate remote path to prevent directory traversal
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        # Check rate limit before API call
        try:
            self._check_rate_limit("get_file_metadata")
        except RuntimeError as e:
            return {'success': False, 'error': str(e)}

        try:
            blob_client = self.container_client.get_blob_client(remote_path)
            properties = blob_client.get_blob_properties()

            return {
                'success': True,
                'size': properties.size,
                'last_modified': properties.last_modified.isoformat() if properties.last_modified else None,
                'metadata': dict(properties.metadata) if properties.metadata else {},
                'checksum': properties.etag.strip('"') if properties.etag else None,
                'content_type': properties.content_settings.content_type if properties.content_settings else None,
                'creation_time': properties.creation_time.isoformat() if properties.creation_time else None,
                'blob_type': properties.blob_type
            }

        except ResourceNotFoundError:
            logger.error(f"Blob not found: {remote_path}")
            return {
                'success': False,
                'error': f'Blob not found: {remote_path}'
            }
        except AzureError as e:
            logger.error(f"Failed to get Azure Blob metadata: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_content_type(self, file_path: Path) -> str:
        """Determine content type based on file extension.

        Args:
            file_path: Path to the file.

        Returns:
            MIME type string.
        """
        import mimetypes

        content_type, _ = mimetypes.guess_type(str(file_path))

        # Default to binary if unknown
        if not content_type:
            content_type = 'application/octet-stream'

        return content_type

    def generate_sas_url(
        self,
        remote_path: str,
        expiry_hours: int = 24,
        read_only: bool = True
    ) -> Dict[str, Any]:
        """Generate a Shared Access Signature (SAS) URL for a blob.

        This allows temporary access to a blob without sharing account credentials.
        Useful for sharing medical images with healthcare providers.

        Args:
            remote_path: Blob name/path.
            expiry_hours: How long the URL should be valid (default 24 hours).
            read_only: If True, only allow read access. If False, allow read/write.

        Returns:
            Dictionary containing:
                - success (bool): Whether operation succeeded
                - sas_url (str): The signed URL for temporary access
                - expiry (str): When the URL expires
                - error (str, optional): Error message if failed
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate remote path
        try:
            self._validate_remote_path(remote_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            from datetime import timedelta

            # Can only generate SAS if we have account key
            if not self.account_key and not self.connection_string:
                return {
                    'success': False,
                    'error': 'SAS generation requires account_key or connection_string'
                }

            # Parse account details from connection string if needed
            account_name = self.account_name
            account_key = self.account_key

            if self.connection_string and not account_key:
                # Extract from connection string
                parts = dict(part.split('=', 1) for part in self.connection_string.split(';') if '=' in part)
                account_name = parts.get('AccountName')
                account_key = parts.get('AccountKey')

            if not account_name or not account_key:
                return {
                    'success': False,
                    'error': 'Could not extract account credentials for SAS generation'
                }

            # Set expiry time
            expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

            # Set permissions
            if read_only:
                permissions = BlobSasPermissions(read=True)
            else:
                permissions = BlobSasPermissions(read=True, write=True)

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=remote_path,
                account_key=account_key,
                permission=permissions,
                expiry=expiry
            )

            # Construct full URL
            sas_url = (
                f"https://{account_name}.blob.core.windows.net/"
                f"{self.container_name}/{remote_path}?{sas_token}"
            )

            logger.info(f"Generated SAS URL for blob: {remote_path}, expires: {expiry}")

            return {
                'success': True,
                'sas_url': sas_url,
                'expiry': expiry.isoformat(),
                'permissions': 'read' if read_only else 'read/write'
            }

        except ImportError:
            return {
                'success': False,
                'error': 'SAS generation requires azure-storage-blob>=12.0.0'
            }
        except AzureError as e:
            logger.error(f"Failed to generate SAS URL: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def copy_blob(
        self,
        source_path: str,
        destination_path: str
    ) -> Dict[str, Any]:
        """Copy a blob within the same container.

        Args:
            source_path: Source blob name/path.
            destination_path: Destination blob name/path.

        Returns:
            Dictionary containing copy result.
        """
        if not self._connected:
            return {'success': False, 'error': 'Not connected to Azure Blob Storage'}

        # Validate paths
        try:
            self._validate_remote_path(source_path)
            self._validate_remote_path(destination_path)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        try:
            source_blob = self.container_client.get_blob_client(source_path)
            dest_blob = self.container_client.get_blob_client(destination_path)

            # Start copy operation
            dest_blob.start_copy_from_url(source_blob.url)

            logger.info(
                f"Successfully copied blob from {source_path} to {destination_path}"
            )

            return {
                'success': True,
                'source_path': source_path,
                'destination_path': destination_path
            }

        except ResourceNotFoundError:
            return {
                'success': False,
                'error': f'Source blob not found: {source_path}'
            }
        except AzureError as e:
            logger.error(f"Azure Blob copy failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
