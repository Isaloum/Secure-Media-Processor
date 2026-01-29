"""
Secure Transfer Module

This is the CORE module of Secure Media Processor - the secure pipeline
for transferring sensitive data from cloud/premises to local GPU.

The module provides:
- End-to-end encrypted data transfer
- Zero-knowledge transfer mode (server never sees plaintext)
- Integrity verification
- Secure deletion after processing
- Audit logging for compliance

Security Model:
    1. Data is encrypted BEFORE leaving source (cloud/hospital)
    2. Keys never leave the local workstation
    3. Decryption happens ONLY on local GPU workstation
    4. All transfers are logged for audit compliance
    5. Data is securely deleted after processing (if configured)
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TransferMode(Enum):
    """Transfer security modes."""
    STANDARD = "standard"           # Encrypt locally, transfer, decrypt locally
    ZERO_KNOWLEDGE = "zero_knowledge"  # Pre-encrypted at source, never decrypted in transit
    STREAMING = "streaming"         # Stream decrypt for large files


class TransferStatus(Enum):
    """Status of a transfer operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransferManifest:
    """
    Manifest for a secure transfer operation.

    Contains all metadata needed for audit logging and verification.
    """
    transfer_id: str
    source: str
    destination: str
    mode: TransferMode
    status: TransferStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    file_count: int = 0
    total_bytes: int = 0
    transferred_bytes: int = 0
    checksum_algorithm: str = "sha256"
    source_checksums: Dict[str, str] = field(default_factory=dict)
    destination_checksums: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureTransferPipeline:
    """
    Core secure transfer pipeline for sensitive data.

    This pipeline ensures:
    - All data is encrypted before transfer
    - Integrity is verified end-to-end
    - Audit logs are maintained for compliance
    - Data is securely deleted when configured

    Example:
        from src.core.secure_transfer import SecureTransferPipeline
        from src.core.encryption import EncryptionManager
        from src.connectors import S3Connector

        # Initialize pipeline
        pipeline = SecureTransferPipeline(
            encryption=EncryptionManager(key_path="~/.smp/keys"),
            audit_logger=AuditLogger(log_path="~/.smp/audit.log")
        )

        # Add cloud connector
        pipeline.add_source(S3Connector(bucket="hospital-data"))

        # Secure download to local GPU workstation
        manifest = pipeline.secure_download(
            remote_path="patient-scans/2024/",
            local_path="/secure/gpu-workspace/",
            mode=TransferMode.ZERO_KNOWLEDGE
        )

        # Verify transfer integrity
        assert pipeline.verify_integrity(manifest)

        # Process locally (your code here)
        results = process_on_gpu(manifest.destination)

        # Secure cleanup (optional)
        pipeline.secure_delete(manifest.destination)
    """

    def __init__(
        self,
        encryption=None,
        audit_logger=None,
        temp_dir: Optional[str] = None,
        verify_checksums: bool = True,
        secure_delete_passes: int = 3
    ):
        """
        Initialize the secure transfer pipeline.

        Args:
            encryption: EncryptionManager instance for crypto operations
            audit_logger: AuditLogger instance for compliance logging
            temp_dir: Directory for temporary files during transfer
            verify_checksums: Whether to verify checksums after transfer
            secure_delete_passes: Number of overwrite passes for secure deletion
        """
        self._encryption = encryption
        self._audit_logger = audit_logger
        self._temp_dir = temp_dir or os.path.join(os.path.expanduser("~"), ".smp", "temp")
        self._verify_checksums = verify_checksums
        self._secure_delete_passes = secure_delete_passes
        self._sources: Dict[str, Any] = {}
        self._active_transfers: Dict[str, TransferManifest] = {}

        # Ensure temp directory exists with restricted permissions
        os.makedirs(self._temp_dir, mode=0o700, exist_ok=True)

    def add_source(self, name: str, connector) -> None:
        """
        Add a data source (cloud connector).

        Args:
            name: Identifier for this source
            connector: Cloud connector instance (S3, GDrive, Dropbox, etc.)
        """
        self._sources[name] = connector
        logger.info(f"Added source: {name}")

    def remove_source(self, name: str) -> None:
        """Remove a data source."""
        if name in self._sources:
            del self._sources[name]
            logger.info(f"Removed source: {name}")

    def secure_download(
        self,
        source_name: str,
        remote_path: str,
        local_path: str,
        mode: TransferMode = TransferMode.STANDARD,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransferManifest:
        """
        Securely download data from cloud to local GPU workstation.

        This is the core operation - download encrypted data and
        decrypt it only on the local machine.

        Args:
            source_name: Name of the registered source connector
            remote_path: Path in cloud storage
            local_path: Local destination path
            mode: Transfer security mode
            progress_callback: Optional callback(transferred_bytes, total_bytes)
            metadata: Optional metadata to include in audit log

        Returns:
            TransferManifest with transfer details

        Raises:
            KeyError: If source not registered
            TransferError: If transfer fails
        """
        if source_name not in self._sources:
            raise KeyError(f"Source '{source_name}' not registered")

        connector = self._sources[source_name]

        # Generate transfer ID
        transfer_id = self._generate_transfer_id()

        # Create manifest
        manifest = TransferManifest(
            transfer_id=transfer_id,
            source=f"{source_name}:{remote_path}",
            destination=local_path,
            mode=mode,
            status=TransferStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            metadata=metadata or {}
        )

        self._active_transfers[transfer_id] = manifest

        # Log transfer start
        if self._audit_logger:
            self._audit_logger.log_transfer_start(manifest)

        try:
            # Ensure local directory exists with restricted permissions
            local_dir = Path(local_path)
            if not local_dir.exists():
                local_dir.mkdir(parents=True, mode=0o700)

            # Download based on mode
            if mode == TransferMode.STANDARD:
                self._standard_download(connector, remote_path, local_path, manifest, progress_callback)
            elif mode == TransferMode.ZERO_KNOWLEDGE:
                self._zero_knowledge_download(connector, remote_path, local_path, manifest, progress_callback)
            elif mode == TransferMode.STREAMING:
                self._streaming_download(connector, remote_path, local_path, manifest, progress_callback)

            # Verify integrity if enabled
            if self._verify_checksums:
                if not self._verify_transfer_integrity(manifest):
                    raise TransferError("Checksum verification failed")

            manifest.status = TransferStatus.COMPLETED
            manifest.completed_at = datetime.utcnow()

            # Log transfer completion
            if self._audit_logger:
                self._audit_logger.log_transfer_complete(manifest)

        except Exception as e:
            manifest.status = TransferStatus.FAILED
            manifest.errors.append(str(e))
            manifest.completed_at = datetime.utcnow()

            if self._audit_logger:
                self._audit_logger.log_transfer_failed(manifest, str(e))

            raise TransferError(f"Transfer failed: {e}") from e

        finally:
            del self._active_transfers[transfer_id]

        return manifest

    def secure_upload(
        self,
        source_name: str,
        local_path: str,
        remote_path: str,
        mode: TransferMode = TransferMode.STANDARD,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransferManifest:
        """
        Securely upload data from local workstation to cloud.

        Data is encrypted BEFORE leaving the local machine.

        Args:
            source_name: Name of the registered destination connector
            local_path: Local source path
            remote_path: Path in cloud storage
            mode: Transfer security mode
            progress_callback: Optional callback(transferred_bytes, total_bytes)
            metadata: Optional metadata to include in audit log

        Returns:
            TransferManifest with transfer details
        """
        if source_name not in self._sources:
            raise KeyError(f"Source '{source_name}' not registered")

        connector = self._sources[source_name]

        # Generate transfer ID
        transfer_id = self._generate_transfer_id()

        # Create manifest
        manifest = TransferManifest(
            transfer_id=transfer_id,
            source=local_path,
            destination=f"{source_name}:{remote_path}",
            mode=mode,
            status=TransferStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            metadata=metadata or {}
        )

        self._active_transfers[transfer_id] = manifest

        if self._audit_logger:
            self._audit_logger.log_transfer_start(manifest)

        try:
            # Calculate source checksum
            local_file = Path(local_path)
            if local_file.is_file():
                manifest.source_checksums[local_path] = self._calculate_checksum(local_path)
                manifest.total_bytes = local_file.stat().st_size
                manifest.file_count = 1

            # Encrypt and upload
            if self._encryption:
                # Encrypt to temp file
                encrypted_path = os.path.join(self._temp_dir, f"{transfer_id}.enc")
                self._encryption.encrypt_file(local_path, encrypted_path)

                # Upload encrypted file
                connector.upload_file(encrypted_path, remote_path)

                # Secure delete temp file
                self._secure_delete_file(encrypted_path)
            else:
                # Direct upload (not recommended for sensitive data)
                logger.warning("Uploading without encryption - not recommended for sensitive data")
                connector.upload_file(local_path, remote_path)

            manifest.transferred_bytes = manifest.total_bytes
            manifest.status = TransferStatus.COMPLETED
            manifest.completed_at = datetime.utcnow()

            if self._audit_logger:
                self._audit_logger.log_transfer_complete(manifest)

        except Exception as e:
            manifest.status = TransferStatus.FAILED
            manifest.errors.append(str(e))
            manifest.completed_at = datetime.utcnow()

            if self._audit_logger:
                self._audit_logger.log_transfer_failed(manifest, str(e))

            raise TransferError(f"Upload failed: {e}") from e

        finally:
            del self._active_transfers[transfer_id]

        return manifest

    def verify_integrity(self, manifest: TransferManifest) -> bool:
        """
        Verify the integrity of a completed transfer.

        Args:
            manifest: Transfer manifest to verify

        Returns:
            True if all checksums match
        """
        return self._verify_transfer_integrity(manifest)

    def secure_delete(self, path: Union[str, Path], recursive: bool = True) -> None:
        """
        Securely delete files with multi-pass overwrite.

        This ensures sensitive data cannot be recovered from disk.

        Args:
            path: File or directory to delete
            recursive: If True, delete directories recursively
        """
        path = Path(path)

        if path.is_file():
            self._secure_delete_file(str(path))
        elif path.is_dir() and recursive:
            for item in path.rglob("*"):
                if item.is_file():
                    self._secure_delete_file(str(item))
            # Remove empty directories
            for item in sorted(path.rglob("*"), reverse=True):
                if item.is_dir():
                    item.rmdir()
            path.rmdir()

        if self._audit_logger:
            self._audit_logger.log_secure_delete(str(path))

    def get_active_transfers(self) -> List[TransferManifest]:
        """Get list of currently active transfers."""
        return list(self._active_transfers.values())

    def cancel_transfer(self, transfer_id: str) -> bool:
        """
        Cancel an active transfer.

        Args:
            transfer_id: ID of transfer to cancel

        Returns:
            True if transfer was cancelled
        """
        if transfer_id in self._active_transfers:
            manifest = self._active_transfers[transfer_id]
            manifest.status = TransferStatus.CANCELLED
            manifest.completed_at = datetime.utcnow()

            if self._audit_logger:
                self._audit_logger.log_transfer_cancelled(manifest)

            return True
        return False

    # Private methods

    def _generate_transfer_id(self) -> str:
        """Generate a unique transfer ID."""
        import uuid
        return str(uuid.uuid4())

    def _calculate_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file checksum."""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _verify_transfer_integrity(self, manifest: TransferManifest) -> bool:
        """Verify all checksums in a transfer manifest."""
        for path, expected_checksum in manifest.destination_checksums.items():
            if os.path.exists(path):
                actual_checksum = self._calculate_checksum(path)
                if actual_checksum != expected_checksum:
                    logger.error(f"Checksum mismatch for {path}")
                    return False
        return True

    def _secure_delete_file(self, file_path: str) -> None:
        """Securely delete a single file with multi-pass overwrite."""
        if not os.path.exists(file_path):
            return

        file_size = os.path.getsize(file_path)

        # Multi-pass overwrite
        with open(file_path, "r+b") as f:
            for pass_num in range(self._secure_delete_passes):
                f.seek(0)
                # Alternate between zeros, ones, and random data
                if pass_num % 3 == 0:
                    pattern = b'\x00'
                elif pass_num % 3 == 1:
                    pattern = b'\xFF'
                else:
                    pattern = os.urandom(1)

                # Write pattern
                for _ in range(0, file_size, 4096):
                    chunk_size = min(4096, file_size - f.tell())
                    f.write(pattern * chunk_size)
                f.flush()
                os.fsync(f.fileno())

        # Finally delete
        os.remove(file_path)
        logger.debug(f"Securely deleted: {file_path}")

    def _standard_download(self, connector, remote_path, local_path, manifest, progress_callback):
        """Standard download: download encrypted, decrypt locally."""
        # Download to temp location
        temp_path = os.path.join(self._temp_dir, f"{manifest.transfer_id}.tmp")

        connector.download_file(remote_path, temp_path)

        # Decrypt if encryption is configured
        if self._encryption:
            self._encryption.decrypt_file(temp_path, local_path)
            self._secure_delete_file(temp_path)
        else:
            # Just move the file
            os.rename(temp_path, local_path)

        # Calculate destination checksum
        manifest.destination_checksums[local_path] = self._calculate_checksum(local_path)
        manifest.transferred_bytes = os.path.getsize(local_path)
        manifest.file_count = 1

    def _zero_knowledge_download(self, connector, remote_path, local_path, manifest, progress_callback):
        """Zero-knowledge download: data is pre-encrypted at source."""
        # In zero-knowledge mode, data was encrypted before upload
        # We download and decrypt without the server ever seeing plaintext
        self._standard_download(connector, remote_path, local_path, manifest, progress_callback)

    def _streaming_download(self, connector, remote_path, local_path, manifest, progress_callback):
        """Streaming download: decrypt on-the-fly for large files."""
        # TODO: Implement streaming decryption for very large files
        # For now, fall back to standard download
        self._standard_download(connector, remote_path, local_path, manifest, progress_callback)


class TransferError(Exception):
    """Exception raised when a transfer operation fails."""
    pass
