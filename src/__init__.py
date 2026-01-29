"""
Secure Media Processor

A secure data pipeline for transferring sensitive data from cloud/premises
to local GPU processing.

Core Mission:
    Provide a safe, secure way to download and process sensitive data
    (medical images, confidential documents, etc.) on local GPU workstations
    instead of leaving it vulnerable in the cloud.

Key Features:
    - End-to-end encryption (AES-256-GCM)
    - Multi-cloud connectors (S3, Google Drive, Dropbox)
    - Zero-knowledge transfer mode
    - HIPAA/GDPR compliant audit logging
    - Secure key exchange for multi-party transfers
    - Secure deletion after processing

Quick Start:
    from secure_media_processor import Pipeline, TransferMode

    # Initialize secure pipeline
    pipeline = Pipeline(
        encryption_key="~/.smp/keys",
        audit_log="~/.smp/audit"
    )

    # Add cloud source
    pipeline.add_cloud("s3", bucket="hospital-data", region="us-east-1")

    # Secure download to local GPU workstation
    manifest = pipeline.secure_download(
        source="s3",
        remote_path="patient-scans/",
        local_path="/secure/gpu-workspace/",
        mode=TransferMode.ZERO_KNOWLEDGE
    )

    # Process locally (data never leaves your machine)
    results = your_processing_function(manifest.destination)

    # Secure cleanup
    pipeline.secure_delete(manifest.destination)

For medical imaging processing, install the optional plugin:
    pip install secure-media-processor[medical]

Documentation:
    https://github.com/Isaloum/Secure-Media-Processor
"""

__version__ = "2.0.0"
__author__ = "Ihab Saloum"

# Core pipeline (the main value proposition)
from .core.secure_transfer import (
    SecureTransferPipeline as Pipeline,
    TransferMode,
    TransferStatus,
    TransferManifest,
    TransferError
)

# Encryption
from .core.encryption import MediaEncryptor

# Audit logging for compliance
from .core.audit_logger import AuditLogger, AuditEventType

# Key exchange for secure multi-party transfers
from .core.key_exchange import KeyExchangeManager, KeyType

# Cloud connectors
from .connectors import (
    ConnectorManager,
    S3Connector,
    GoogleDriveConnector,
    DropboxConnector
)

__all__ = [
    # Version
    '__version__',
    # Core pipeline
    'Pipeline',
    'TransferMode',
    'TransferStatus',
    'TransferManifest',
    'TransferError',
    # Encryption
    'MediaEncryptor',
    # Audit
    'AuditLogger',
    'AuditEventType',
    # Key exchange
    'KeyExchangeManager',
    'KeyType',
    # Cloud connectors
    'ConnectorManager',
    'S3Connector',
    'GoogleDriveConnector',
    'DropboxConnector',
]
