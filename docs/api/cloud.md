# Cloud Storage API Reference

The cloud package provides multi-cloud storage integration with S3, Google Drive, and Dropbox.

## Location

```
src/cloud/
├── __init__.py
├── legacy.py              # Backward-compat CloudStorageManager
└── connectors/
    ├── __init__.py
    ├── base.py            # Abstract base class
    ├── manager.py         # Multi-connector management
    ├── s3.py              # AWS S3 connector
    ├── google_drive.py    # Google Drive connector
    └── dropbox.py         # Dropbox connector
```

---

## base.py - CloudConnector

Abstract base class for all cloud connectors.

```python
from src.cloud.connectors.base import CloudConnector
```

### Abstract Methods

All connectors implement these methods:

```python
def upload_file(self, local_path: str, remote_path: str) -> Dict[str, Any]
def download_file(self, remote_path: str, local_path: str) -> Dict[str, Any]
def delete_file(self, remote_path: str) -> Dict[str, Any]
def list_files(self, prefix: str = "") -> List[Dict[str, Any]]
def get_file_metadata(self, remote_path: str) -> Dict[str, Any]
```

---

## s3.py - S3Connector

AWS S3 storage connector.

```python
from src.cloud.connectors import S3Connector
```

### Constructor

```python
S3Connector(
    bucket_name: str,
    region: str = "us-east-1",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `bucket_name` | `str` | S3 bucket name |
| `region` | `str` | AWS region |
| `access_key` | `str` | AWS access key (or use env var) |
| `secret_key` | `str` | AWS secret key (or use env var) |

### Methods

#### upload_file()

```python
def upload_file(
    self,
    local_path: str,
    remote_path: str,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]
```

**Returns:**
```python
{
    'success': True,
    'remote_key': 'path/to/file.enc',
    'size': 1024,
    'checksum': 'abc123...',
    'etag': '"abc123..."'
}
```

#### download_file()

```python
def download_file(
    self,
    remote_path: str,
    local_path: str,
    verify_checksum: bool = True
) -> Dict[str, Any]
```

### Example

```python
from src.cloud.connectors import S3Connector

# Connect to S3
s3 = S3Connector(
    bucket_name="my-secure-bucket",
    region="us-west-2"
)

# Upload encrypted file
result = s3.upload_file("local/file.enc", "backups/file.enc")
print(f"Uploaded to: {result['remote_key']}")

# Download and verify
result = s3.download_file("backups/file.enc", "restored.enc")
print(f"Checksum valid: {result['checksum_verified']}")

# List files
files = s3.list_files(prefix="backups/")
for f in files:
    print(f"{f['key']}: {f['size']} bytes")
```

---

## google_drive.py - GoogleDriveConnector

Google Drive storage connector.

```python
from src.cloud.connectors import GoogleDriveConnector
```

### Constructor

```python
GoogleDriveConnector(
    credentials_path: Optional[str] = None,
    folder_id: Optional[str] = None
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `credentials_path` | `str` | Path to service account JSON |
| `folder_id` | `str` | Root folder ID for operations |

### Example

```python
from src.cloud.connectors import GoogleDriveConnector

drive = GoogleDriveConnector(
    credentials_path="service-account.json",
    folder_id="1ABC..."  # Optional root folder
)

# Upload
result = drive.upload_file("report.enc", "reports/2024/report.enc")

# Files are organized in folder hierarchy
files = drive.list_files(prefix="reports/")
```

---

## dropbox.py - DropboxConnector

Dropbox storage connector.

```python
from src.cloud.connectors import DropboxConnector
```

### Constructor

```python
DropboxConnector(
    access_token: Optional[str] = None
)
```

### Example

```python
from src.cloud.connectors import DropboxConnector

dropbox = DropboxConnector()  # Uses DROPBOX_ACCESS_TOKEN env var

# Upload
result = dropbox.upload_file("data.enc", "/Backups/data.enc")

# Download
result = dropbox.download_file("/Backups/data.enc", "restored.enc")
```

---

## manager.py - ConnectorManager

Manage multiple cloud connectors and sync operations.

```python
from src.cloud.connectors import ConnectorManager
```

### Constructor

```python
ConnectorManager()
```

### Methods

#### register_connector()

```python
def register_connector(
    self,
    name: str,
    connector: CloudConnector
) -> None
```

#### sync_file()

```python
def sync_file(
    self,
    local_path: str,
    remote_path: str,
    connectors: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]
```

Sync a file to multiple cloud providers.

### Example

```python
from src.cloud.connectors import (
    ConnectorManager,
    S3Connector,
    GoogleDriveConnector,
    DropboxConnector
)

# Create manager
manager = ConnectorManager()

# Register connectors
manager.register_connector("s3", S3Connector(bucket_name="backup"))
manager.register_connector("drive", GoogleDriveConnector())
manager.register_connector("dropbox", DropboxConnector())

# Sync to all clouds at once
results = manager.sync_file(
    "important.enc",
    "backups/important.enc"
)

for provider, result in results.items():
    print(f"{provider}: {'✓' if result['success'] else '✗'}")
```

---

## Security Features

### Path Validation

All connectors validate remote paths to prevent path traversal attacks:

```python
# These will raise ValueError:
connector.upload_file("file.txt", "../../../etc/passwd")
connector.upload_file("file.txt", "/etc/shadow")
connector.upload_file("file.txt", "test\x00file")  # Null byte

# These are valid:
connector.upload_file("file.txt", "documents/report.pdf")
connector.upload_file("file.txt", "backup/2024/data.enc")
```

### Credential Management

Credentials are cleared from memory when connectors are destroyed:

```python
connector = S3Connector(...)
# ... use connector ...
del connector  # Credentials cleared from memory
```

---

## Backward Compatibility

Legacy imports still work:

```python
# Legacy
from src.connectors import S3Connector
from src.cloud_storage import CloudStorageManager

# New (recommended)
from src.cloud.connectors import S3Connector
from src.cloud.connectors import ConnectorManager
```
