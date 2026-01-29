"""Core functionality for Secure Media Processor.

This package provides core infrastructure components:
- encryption: AES-256-GCM file encryption
- config: Application settings management
- rate_limiter: API rate limiting utilities
- secure_transfer: Core secure transfer pipeline
- audit_logger: Compliance-ready audit logging
- key_exchange: Secure key exchange mechanisms
"""

from .encryption import MediaEncryptor
from .config import Settings, settings
from .rate_limiter import RateLimiter, RateLimitConfig
from .secure_transfer import (
    SecureTransferPipeline,
    TransferMode,
    TransferStatus,
    TransferManifest,
    TransferError
)
from .audit_logger import AuditLogger, AuditEventType, AuditEntry
from .key_exchange import KeyExchangeManager, KeyType, KeyPair, DerivedKey

__all__ = [
    # Encryption
    'MediaEncryptor',
    # Config
    'Settings',
    'settings',
    # Rate limiting
    'RateLimiter',
    'RateLimitConfig',
    # Secure transfer (NEW - Core feature)
    'SecureTransferPipeline',
    'TransferMode',
    'TransferStatus',
    'TransferManifest',
    'TransferError',
    # Audit logging (NEW - Compliance)
    'AuditLogger',
    'AuditEventType',
    'AuditEntry',
    # Key exchange (NEW - Security)
    'KeyExchangeManager',
    'KeyType',
    'KeyPair',
    'DerivedKey',
]
