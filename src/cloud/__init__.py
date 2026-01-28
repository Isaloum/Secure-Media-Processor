"""Cloud storage package for Secure Media Processor.

This package provides cloud storage functionality:
- connectors: Provider-specific connectors (S3, Google Drive, Dropbox)
- legacy: Backward-compatible CloudStorageManager

Example:
    >>> from src.cloud import ConnectorManager
    >>> manager = ConnectorManager()
    >>> manager.add_connector('s3', bucket='my-bucket')
"""

from .legacy import CloudStorageManager

# Import connectors subpackage
from .connectors import (
    BaseConnector,
    ConnectorManager,
    S3Connector,
    GoogleDriveConnector,
    DropboxConnector,
)

__all__ = [
    # Legacy
    'CloudStorageManager',
    # Connectors
    'BaseConnector',
    'ConnectorManager',
    'S3Connector',
    'GoogleDriveConnector',
    'DropboxConnector',
]
