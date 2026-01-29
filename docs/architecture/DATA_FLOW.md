# Data Flow Architecture

## Overview

This document describes how data moves through the Secure Media Processor pipeline, from cloud sources to local GPU processing and back.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SECURE MEDIA PROCESSOR                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │
│   │   INGEST    │    │   SECURE    │    │   LOCAL     │    │  EXPORT   │  │
│   │   LAYER     │───►│   TRANSIT   │───►│   PROCESS   │───►│  LAYER    │  │
│   │             │    │   LAYER     │    │   LAYER     │    │           │  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └───────────┘  │
│         │                  │                  │                  │         │
│    Cloud APIs         Encryption         GPU/CPU            Results       │
│    • S3              • AES-256-GCM       Processing         • Local       │
│    • Google Drive    • Key Exchange      • Plugins          • Encrypted   │
│    • Dropbox         • Integrity                            • Cloud       │
│    • SFTP                                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Ingest Layer

The ingest layer handles connections to data sources:

```python
from src.connectors import ConnectorManager, S3Connector

# Initialize connectors
manager = ConnectorManager()
manager.add_connector('hospital-s3', S3Connector(
    bucket_name='patient-data',
    region='us-east-1'
))

# List available files
files = manager.list_files('hospital-s3', prefix='scans/2024/')
```

**Supported Sources:**
- AWS S3 (production)
- Google Drive (production)
- Dropbox (production)
- Azure Blob Storage (planned)
- SFTP/SCP (planned)
- DICOM PACS (planned)

### 2. Secure Transit Layer

The transit layer ensures data is encrypted end-to-end:

```python
from src.core import SecureTransferPipeline, TransferMode

pipeline = SecureTransferPipeline(
    encryption=encryption_manager,
    audit_logger=audit_logger
)

# Secure download with zero-knowledge mode
manifest = pipeline.secure_download(
    source_name='hospital-s3',
    remote_path='scans/patient-001/',
    local_path='/secure/workspace/',
    mode=TransferMode.ZERO_KNOWLEDGE
)
```

**Security Features:**
- AES-256-GCM encryption
- ECDH key exchange
- SHA-256 integrity verification
- Audit logging

### 3. Local Process Layer

Processing happens entirely on the local GPU workstation:

```python
# Data is now local and decrypted
# Use any processing tool/plugin
from smp_medical import MedicalImagingPlugin

plugin = MedicalImagingPlugin()
results = plugin.process(manifest.destination, operation='segment')
```

**Plugin Architecture:**
- Medical imaging (DICOM, U-Net)
- Video processing (planned)
- Custom processors

### 4. Export Layer

Results can be saved locally or uploaded (encrypted):

```python
# Save locally
results.save('/results/patient-001/')

# Or upload encrypted results
pipeline.secure_upload(
    source_name='results-s3',
    local_path='/results/patient-001/',
    remote_path='processed/patient-001/',
    mode=TransferMode.STANDARD
)

# Clean up
pipeline.secure_delete('/secure/workspace/')
```

## Detailed Data Flow

### Download Flow

```
                    CLOUD                          LOCAL
                      │                              │
    1. List files     │                              │
    ──────────────────►                              │
                      │                              │
    2. Metadata       │                              │
    ◄──────────────────                              │
                      │                              │
                      │    3. Request download       │
                      │◄──────────────────────────────
                      │                              │
    4. Encrypted      │                              │
       stream         │─────────────────────────────►│
                      │                              │
                      │                              │ 5. Write to temp
                      │                              │    (still encrypted)
                      │                              │
                      │                              │ 6. Verify checksum
                      │                              │
                      │                              │ 7. Decrypt
                      │                              │
                      │                              │ 8. Write to destination
                      │                              │
                      │                              │ 9. Secure delete temp
                      │                              │
                      │                              │ 10. Audit log entry
```

### Upload Flow

```
                    LOCAL                          CLOUD
                      │                              │
    1. Read file      │                              │
                      │                              │
    2. Calculate      │                              │
       checksum       │                              │
                      │                              │
    3. Encrypt to     │                              │
       temp file      │                              │
                      │                              │
    4. Upload         │                              │
       encrypted      │─────────────────────────────►│
                      │                              │
                      │    5. Confirm receipt        │
                      │◄──────────────────────────────
                      │                              │
    6. Secure delete  │                              │
       temp file      │                              │
                      │                              │
    7. Audit log      │                              │
       entry          │                              │
```

## Data States

Data exists in different states as it moves through the pipeline:

| State | Location | Encryption | Access |
|-------|----------|------------|--------|
| At rest (cloud) | S3/GDrive/Dropbox | Encrypted (AES-256-GCM) | Cloud provider |
| In transit | Network | Encrypted (AES-256-GCM + TLS) | None |
| Temp storage | Local temp dir | Encrypted | SMP only |
| Processing | Local destination | Decrypted (plaintext) | User/Plugins |
| GPU memory | GPU RAM | Decrypted | GPU process |
| Results | Local/Cloud | User choice | User |

## Directory Structure

### Local Workspace

```
~/.smp/
├── keys/               # Encrypted key storage
│   ├── .master         # Master key
│   ├── .salt           # PBKDF2 salt
│   └── *.key           # Key pairs
├── temp/               # Temporary transfer files
│   └── *.tmp           # Encrypted during transfer
├── audit/              # Audit logs
│   └── audit_*.jsonl   # Daily log files
└── config/             # Configuration
    └── settings.json

/secure/workspace/      # Example processing workspace
├── input/              # Downloaded decrypted files
├── output/             # Processing results
└── models/             # ML models (if using plugins)
```

## Transfer Manifest

Each transfer creates a manifest tracking its state:

```python
@dataclass
class TransferManifest:
    transfer_id: str              # Unique identifier
    source: str                   # e.g., "hospital-s3:/scans/"
    destination: str              # e.g., "/secure/workspace/"
    mode: TransferMode            # STANDARD, ZERO_KNOWLEDGE, STREAMING
    status: TransferStatus        # PENDING, IN_PROGRESS, COMPLETED, FAILED
    started_at: datetime
    completed_at: datetime
    file_count: int
    total_bytes: int
    transferred_bytes: int
    checksum_algorithm: str       # "sha256"
    source_checksums: Dict        # File -> checksum
    destination_checksums: Dict   # File -> checksum
    errors: List[str]
    metadata: Dict                # Custom metadata
```

## Error Handling

### Retry Logic

```python
# Built-in retry with exponential backoff
pipeline = SecureTransferPipeline(
    retry_config={
        'max_retries': 4,
        'backoff_base': 2,  # seconds
        'backoff_max': 60
    }
)
```

### Partial Transfer Recovery

If a transfer fails midway:

1. Check manifest for `transferred_bytes`
2. Resume from last successful chunk
3. Verify checksums on completion

### Integrity Failures

If checksum verification fails:

1. Manifest marked as `FAILED`
2. Audit log entry created
3. Corrupt file quarantined (not deleted)
4. User notified

## Performance Considerations

### Parallel Transfers

```python
# Enable parallel chunk downloads
manifest = pipeline.secure_download(
    ...,
    parallel_chunks=4,  # Download 4 chunks simultaneously
    chunk_size_mb=64
)
```

### Streaming Mode

For very large files:

```python
# Stream decrypt (doesn't load entire file into memory)
manifest = pipeline.secure_download(
    ...,
    mode=TransferMode.STREAMING
)
```

### Bandwidth Limiting

```python
# Limit bandwidth to avoid network saturation
pipeline = SecureTransferPipeline(
    bandwidth_limit_mbps=100
)
```

## Integration Points

### With Medical Imaging Plugin

```python
from src import Pipeline, TransferMode
from plugins.smp_medical import MedicalImagingPlugin

# Setup
pipeline = Pipeline()
medical = MedicalImagingPlugin()

# Download DICOM files
manifest = pipeline.secure_download(
    source='hospital',
    remote_path='dicom/study-001/',
    local_path='/workspace/dicom/'
)

# Process with plugin
results = medical.process(
    manifest.destination,
    operation='segment',
    model='unet-breast-mri'
)

# Clean up
pipeline.secure_delete(manifest.destination)
```

### With External Tools

SMP downloads and decrypts data locally. After that, you can use any tool:

```python
# After secure download, data is just local files
import pydicom
import nibabel

# Use any DICOM tool
ds = pydicom.dcmread('/workspace/dicom/image.dcm')

# Use any NIfTI tool
img = nibabel.load('/workspace/nifti/brain.nii.gz')

# Run any ML model
model = load_model('my_model.pt')
predictions = model(data)
```

## Monitoring

### Progress Callbacks

```python
def progress_handler(transferred: int, total: int):
    percent = (transferred / total) * 100
    print(f"Progress: {percent:.1f}%")

manifest = pipeline.secure_download(
    ...,
    progress_callback=progress_handler
)
```

### Active Transfers

```python
# Check what's currently transferring
active = pipeline.get_active_transfers()
for manifest in active:
    print(f"{manifest.transfer_id}: {manifest.status}")
```

### Audit Trail

```python
# Export transfer history for review
audit.export_logs(
    output_path='transfers_2024.json',
    start_date='2024-01-01',
    event_types=[AuditEventType.TRANSFER_COMPLETE]
)
```
