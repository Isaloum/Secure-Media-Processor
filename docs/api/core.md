# Core Modules API Reference

The core package provides fundamental functionality for encryption, configuration, and rate limiting.

## Location

```
src/core/
├── __init__.py
├── encryption.py    # AES-256-GCM encryption
├── config.py        # Settings management
└── rate_limiter.py  # API rate limiting
```

---

## encryption.py

### MediaEncryptor

Military-grade AES-256-GCM encryption for media files.

```python
from src.core.encryption import MediaEncryptor
```

#### Constructor

```python
MediaEncryptor(key_path: Optional[str] = None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `key_path` | `str` | Path to encryption key file. If not provided, generates new key. |

#### Methods

##### encrypt_file()

```python
def encrypt_file(
    self,
    input_path: str,
    output_path: str
) -> Dict[str, Any]
```

Encrypts a file using AES-256-GCM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | Path to file to encrypt |
| `output_path` | `str` | Path for encrypted output |

**Returns:** Dictionary with:
- `original_size`: Original file size in bytes
- `encrypted_size`: Encrypted file size in bytes
- `algorithm`: Encryption algorithm used
- `checksum`: SHA-256 checksum of original

##### decrypt_file()

```python
def decrypt_file(
    self,
    input_path: str,
    output_path: str
) -> Dict[str, Any]
```

Decrypts an encrypted file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_path` | `str` | Path to encrypted file |
| `output_path` | `str` | Path for decrypted output |

**Returns:** Dictionary with:
- `encrypted_size`: Encrypted file size
- `decrypted_size`: Decrypted file size
- `checksum_valid`: Whether integrity check passed

#### Example

```python
from src.core.encryption import MediaEncryptor

# Create encryptor (generates key if none exists)
encryptor = MediaEncryptor("~/.smp/master.key")

# Encrypt a file
result = encryptor.encrypt_file("photo.jpg", "photo.enc")
print(f"Encrypted {result['original_size']} bytes")

# Decrypt it back
result = encryptor.decrypt_file("photo.enc", "photo_restored.jpg")
print(f"Checksum valid: {result['checksum_valid']}")
```

---

## config.py

### Settings

Application configuration using environment variables and defaults.

```python
from src.core.config import settings
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `master_key_path` | `str` | Path to encryption master key |
| `aws_access_key_id` | `str` | AWS access key |
| `aws_secret_access_key` | `str` | AWS secret key |
| `aws_region` | `str` | AWS region (default: us-east-1) |
| `aws_bucket_name` | `str` | Default S3 bucket |
| `google_credentials_path` | `str` | Path to Google service account JSON |
| `dropbox_access_token` | `str` | Dropbox API token |

#### Environment Variables

```bash
export SMP_MASTER_KEY_PATH="~/.smp/master.key"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
export AWS_BUCKET_NAME="my-bucket"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/creds.json"
export DROPBOX_ACCESS_TOKEN="sl...."
```

---

## rate_limiter.py

### RateLimiter

Token bucket rate limiter for API operations.

```python
from src.core.rate_limiter import RateLimiter
```

#### Constructor

```python
RateLimiter(
    rate: float = 10.0,
    burst: int = 20
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `rate` | `float` | Requests per second |
| `burst` | `int` | Maximum burst size |

#### Methods

##### acquire()

```python
def acquire(self, tokens: int = 1) -> bool
```

Attempt to acquire tokens. Returns `True` if allowed, `False` if rate limited.

##### wait()

```python
async def wait(self, tokens: int = 1) -> None
```

Wait until tokens are available (async).

#### Example

```python
from src.core.rate_limiter import RateLimiter

# 10 requests/second, burst of 20
limiter = RateLimiter(rate=10.0, burst=20)

for file in files:
    if limiter.acquire():
        upload_file(file)
    else:
        time.sleep(0.1)  # Wait and retry
```

---

## Backward Compatibility

Legacy imports still work:

```python
# These both work:
from src.encryption import MediaEncryptor  # Legacy
from src.core.encryption import MediaEncryptor  # New
```
