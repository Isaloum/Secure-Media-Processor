"""Cloud storage connectors module.

This module provides a unified interface for connecting to various cloud storage
providers including AWS S3, Google Drive, Dropbox, Azure Blob Storage, and OneDrive.

Example:
    Basic usage with a single connector:

    >>> from src.connectors import S3Connector
    >>>
    >>> connector = S3Connector(bucket_name='my-bucket', region='us-east-1')
    >>> connector.connect()
    >>> result = connector.upload_file('local.txt', 'remote.txt')
    >>> connector.disconnect()

    Using Azure Blob Storage:

    >>> from src.connectors import AzureBlobConnector
    >>>
    >>> connector = AzureBlobConnector(
    ...     connection_string="DefaultEndpointsProtocol=https;...",
    ...     container_name="medical-data"
    ... )
    >>> connector.connect()
    >>> result = connector.upload_file('scan.dcm', 'studies/scan.dcm')

    Using OneDrive:

    >>> from src.connectors import OneDriveConnector
    >>>
    >>> connector = OneDriveConnector(
    ...     client_id="your-app-id",
    ...     client_secret="your-secret",
    ...     tenant_id="your-tenant-id"
    ... )
    >>> connector.connect()
    >>> result = connector.upload_file('scan.dcm', 'medical/scans/scan.dcm')

    Using the connector manager:

    >>> from src.connectors import ConnectorManager, S3Connector, DropboxConnector
    >>>
    >>> manager = ConnectorManager()
    >>> manager.add_connector('s3', S3Connector(bucket_name='my-bucket'))
    >>> manager.add_connector('dropbox', DropboxConnector(access_token='token'))
    >>>
    >>> # Connect all
    >>> manager.connect_all()
    >>>
    >>> # Upload using active connector
    >>> manager.upload_file('file.txt', 'remote/file.txt')
    >>>
    >>> # Upload to specific connector
    >>> manager.upload_file('file.txt', 'file.txt', connector_name='dropbox')
"""

from .base_connector import CloudConnector
from .s3_connector import S3Connector
from .google_drive_connector import GoogleDriveConnector
from .dropbox_connector import DropboxConnector
from .onedrive_connector import OneDriveConnector
from .connector_manager import ConnectorManager

# Azure connector is optional (requires azure-storage-blob)
try:
    from .azure_blob_connector import AzureBlobConnector
    AZURE_AVAILABLE = True
except ImportError:
    AzureBlobConnector = None  # type: ignore
    AZURE_AVAILABLE = False


__all__ = [
    'CloudConnector',
    'S3Connector',
    'GoogleDriveConnector',
    'DropboxConnector',
    'OneDriveConnector',
    'AzureBlobConnector',
    'ConnectorManager',
    'AZURE_AVAILABLE',
]


__version__ = '1.2.0'
