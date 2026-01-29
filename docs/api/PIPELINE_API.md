# Pipeline API Reference

## SecureTransferPipeline

The core class for secure data transfer operations.

### Import

```python
from src.core import SecureTransferPipeline, TransferMode, TransferStatus
# Or from the main package:
from src import Pipeline, TransferMode
```

### Constructor

```python
SecureTransferPipeline(
    encryption=None,           # EncryptionManager instance
    audit_logger=None,         # AuditLogger instance
    temp_dir=None,             # Temporary file directory (default: ~/.smp/temp)
    verify_checksums=True,     # Verify checksums after transfer
    secure_delete_passes=3     # Number of overwrite passes for secure deletion
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `encryption` | `MediaEncryptor` | `None` | Encryption manager for crypto operations |
| `audit_logger` | `AuditLogger` | `None` | Logger for compliance audit trail |
| `temp_dir` | `str` | `~/.smp/temp` | Directory for temporary files |
| `verify_checksums` | `bool` | `True` | Whether to verify SHA-256 checksums |
| `secure_delete_passes` | `int` | `3` | Overwrite passes for secure deletion |

**Example:**

```python
from src.core import SecureTransferPipeline, MediaEncryptor, AuditLogger

pipeline = SecureTransferPipeline(
    encryption=MediaEncryptor(key_path="~/.smp/keys/master.key"),
    audit_logger=AuditLogger(log_path="~/.smp/audit/"),
    verify_checksums=True
)
```

---

### Methods

#### add_source

Add a data source (cloud connector).

```python
add_source(name: str, connector: BaseConnector) -> None
```

**Parameters:**
- `name`: Identifier for this source
- `connector`: Cloud connector instance

**Example:**

```python
from src.connectors import S3Connector

pipeline.add_source('hospital', S3Connector(
    bucket_name='patient-data',
    region='us-east-1'
))
```

---

#### remove_source

Remove a data source.

```python
remove_source(name: str) -> None
```

---

#### secure_download

Securely download data from cloud to local GPU workstation.

```python
secure_download(
    source_name: str,
    remote_path: str,
    local_path: str,
    mode: TransferMode = TransferMode.STANDARD,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TransferManifest
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_name` | `str` | Name of the registered source connector |
| `remote_path` | `str` | Path in cloud storage |
| `local_path` | `str` | Local destination path |
| `mode` | `TransferMode` | Transfer security mode (see below) |
| `progress_callback` | `Callable` | Optional progress callback |
| `metadata` | `Dict` | Optional metadata for audit log |

**Returns:** `TransferManifest` with transfer details

**Example:**

```python
def show_progress(transferred, total):
    print(f"{transferred}/{total} bytes")

manifest = pipeline.secure_download(
    source_name='hospital',
    remote_path='scans/patient-001/',
    local_path='/secure/workspace/',
    mode=TransferMode.ZERO_KNOWLEDGE,
    progress_callback=show_progress,
    metadata={'purpose': 'research-study-42'}
)
```

---

#### secure_upload

Securely upload data from local workstation to cloud.

```python
secure_upload(
    source_name: str,
    local_path: str,
    remote_path: str,
    mode: TransferMode = TransferMode.STANDARD,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TransferManifest
```

**Parameters:** Same as `secure_download` (with source/destination swapped)

**Example:**

```python
manifest = pipeline.secure_upload(
    source_name='results-bucket',
    local_path='/results/analysis.json',
    remote_path='processed/patient-001/analysis.json'
)
```

---

#### verify_integrity

Verify the integrity of a completed transfer.

```python
verify_integrity(manifest: TransferManifest) -> bool
```

**Returns:** `True` if all checksums match

---

#### secure_delete

Securely delete files with multi-pass overwrite.

```python
secure_delete(path: Union[str, Path], recursive: bool = True) -> None
```

**Parameters:**
- `path`: File or directory to delete
- `recursive`: If `True`, delete directories recursively

**Example:**

```python
# Delete a single file
pipeline.secure_delete('/workspace/sensitive-data.dcm')

# Delete entire directory
pipeline.secure_delete('/workspace/patient-001/', recursive=True)
```

---

#### get_active_transfers

Get list of currently active transfers.

```python
get_active_transfers() -> List[TransferManifest]
```

---

#### cancel_transfer

Cancel an active transfer.

```python
cancel_transfer(transfer_id: str) -> bool
```

**Returns:** `True` if transfer was cancelled

---

## TransferMode

Enum for transfer security modes.

```python
from src.core import TransferMode
```

| Mode | Description |
|------|-------------|
| `STANDARD` | Encrypt locally, transfer, decrypt locally |
| `ZERO_KNOWLEDGE` | Data pre-encrypted at source; server never sees plaintext |
| `STREAMING` | Stream decrypt for large files (reduced memory usage) |

---

## TransferStatus

Enum for transfer operation status.

```python
from src.core import TransferStatus
```

| Status | Description |
|--------|-------------|
| `PENDING` | Transfer not yet started |
| `IN_PROGRESS` | Currently transferring |
| `COMPLETED` | Transfer finished successfully |
| `FAILED` | Transfer failed (see errors in manifest) |
| `CANCELLED` | Transfer was cancelled |

---

## TransferManifest

Dataclass containing transfer operation details.

```python
from src.core import TransferManifest
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `transfer_id` | `str` | Unique identifier |
| `source` | `str` | Source path (e.g., "s3:bucket/path") |
| `destination` | `str` | Destination path |
| `mode` | `TransferMode` | Security mode used |
| `status` | `TransferStatus` | Current status |
| `started_at` | `datetime` | When transfer started |
| `completed_at` | `datetime` | When transfer completed (or None) |
| `file_count` | `int` | Number of files transferred |
| `total_bytes` | `int` | Total bytes to transfer |
| `transferred_bytes` | `int` | Bytes transferred so far |
| `checksum_algorithm` | `str` | Algorithm used (default: "sha256") |
| `source_checksums` | `Dict[str, str]` | Source file checksums |
| `destination_checksums` | `Dict[str, str]` | Destination file checksums |
| `errors` | `List[str]` | Any error messages |
| `metadata` | `Dict[str, Any]` | Custom metadata |

---

## Complete Example

```python
from src import Pipeline, TransferMode
from src.core import MediaEncryptor, AuditLogger
from src.connectors import S3Connector

# Initialize components
encryption = MediaEncryptor(key_path="~/.smp/keys/master.key")
audit = AuditLogger(log_path="~/.smp/audit/", user_id="researcher@hospital.org")

# Create pipeline
pipeline = Pipeline(
    encryption=encryption,
    audit_logger=audit
)

# Add cloud sources
pipeline.add_source('hospital-data', S3Connector(
    bucket_name='patient-scans',
    region='us-east-1'
))

pipeline.add_source('results-bucket', S3Connector(
    bucket_name='processed-results',
    region='us-east-1'
))

# Download with progress tracking
def on_progress(transferred, total):
    pct = (transferred / total) * 100 if total > 0 else 0
    print(f"\rDownloading: {pct:.1f}%", end="", flush=True)

manifest = pipeline.secure_download(
    source_name='hospital-data',
    remote_path='mri/study-2024-001/',
    local_path='/secure/gpu-workspace/input/',
    mode=TransferMode.ZERO_KNOWLEDGE,
    progress_callback=on_progress
)

print(f"\nDownloaded {manifest.file_count} files ({manifest.total_bytes} bytes)")

# Verify integrity
if pipeline.verify_integrity(manifest):
    print("Integrity verified!")
else:
    print("WARNING: Checksum mismatch!")

# ... do your local GPU processing here ...

# Upload results (encrypted)
results_manifest = pipeline.secure_upload(
    source_name='results-bucket',
    local_path='/secure/gpu-workspace/output/',
    remote_path='results/study-2024-001/'
)

# Secure cleanup
pipeline.secure_delete('/secure/gpu-workspace/')
print("Workspace securely deleted")
```
