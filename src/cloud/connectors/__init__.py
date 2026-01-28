"""Cloud storage connectors package.

Provides unified interface for cloud storage providers:
- S3: AWS S3 connector
- Google Drive: Google Drive API connector
- Dropbox: Dropbox API connector

Example:
    >>> from src.cloud.connectors import S3Connector, ConnectorManager
    >>> connector = S3Connector(bucket_name='my-bucket')
    >>> connector.connect()
"""

from .base import CloudConnector as BaseConnector
from .s3 import S3Connector
from .google_drive import GoogleDriveConnector
from .dropbox import DropboxConnector
from .manager import ConnectorManager

__all__ = [
    'BaseConnector',
    'S3Connector',
    'GoogleDriveConnector',
    'DropboxConnector',
    'ConnectorManager',
]
