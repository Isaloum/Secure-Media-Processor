# System Architecture

Secure Media Processor is a modular, privacy-focused media processing platform with military-grade encryption and multi-cloud support.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Interface                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ crypto  │ │ cloud   │ │ media   │ │ license │ │ medical │ │  main   │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼──────────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │          │
┌───────┼──────────┼──────────┼──────────┼──────────┼──────────┼─────────────┐
│       ▼          ▼          ▼          ▼          ▼          ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Core Services                                │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤   │
│  │ encryption  │   config    │rate_limiter │  licensing  │     gpu     │   │
│  │ AES-256-GCM │  settings   │token bucket │  HMAC keys  │  PyTorch    │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Cloud Connectors                               │   │
│  ├─────────────────┬─────────────────┬─────────────────────────────────┤   │
│  │   S3Connector   │GoogleDriveConn  │   DropboxConnector              │   │
│  │    (AWS S3)     │  (Google API)   │     (Dropbox API)               │   │
│  └────────┬────────┴────────┬────────┴────────┬────────────────────────┘   │
│           │                 │                 │                             │
│           └─────────────────┼─────────────────┘                             │
│                             ▼                                               │
│                    ┌─────────────────┐                                      │
│                    │ConnectorManager │                                      │
│                    │  (multi-cloud)  │                                      │
│                    └─────────────────┘                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Medical Package                                │   │
│  ├───────────────┬───────────────┬───────────────┬─────────────────────┤   │
│  │    dicom      │ preprocessing │     unet      │     inference       │   │
│  │ DICOM reader  │ MRI pipeline  │ segmentation  │  cancer predict     │   │
│  └───────────────┴───────────────┴───────────────┴─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
Secure-Media-Processor/
├── src/                          # Main source code
│   ├── core/                     # Core functionality
│   │   ├── encryption.py         # AES-256-GCM encryption
│   │   ├── config.py             # Settings management
│   │   └── rate_limiter.py       # API rate limiting
│   │
│   ├── cloud/                    # Cloud storage
│   │   ├── legacy.py             # CloudStorageManager (compat)
│   │   └── connectors/           # Provider implementations
│   │       ├── base.py           # Abstract CloudConnector
│   │       ├── manager.py        # Multi-cloud management
│   │       ├── s3.py             # AWS S3
│   │       ├── google_drive.py   # Google Drive
│   │       └── dropbox.py        # Dropbox
│   │
│   ├── medical/                  # Medical imaging
│   │   ├── dicom.py              # DICOM processing
│   │   ├── preprocessing.py      # MRI preprocessing
│   │   ├── unet/                 # U-Net segmentation
│   │   │   ├── models.py         # Network architectures
│   │   │   ├── losses.py         # Loss functions
│   │   │   ├── metrics.py        # Evaluation metrics
│   │   │   ├── postprocessing.py # Mask cleanup
│   │   │   └── inference.py      # Segmentation pipeline
│   │   └── inference/            # ML inference
│   │       ├── config.py         # Configuration
│   │       ├── loaders.py        # Model loaders
│   │       └── pipeline.py       # Prediction pipeline
│   │
│   ├── processing/               # Media processing
│   │   └── gpu.py                # GPU acceleration
│   │
│   ├── licensing/                # License management
│   │   └── manager.py            # HMAC validation
│   │
│   └── cli/                      # Command-line interface
│       ├── main.py               # Entry point
│       ├── crypto.py             # encrypt/decrypt
│       ├── cloud.py              # upload/download
│       ├── media.py              # resize/filter/info
│       ├── license.py            # license commands
│       └── medical.py            # medical commands
│
├── tests/                        # Test suite
├── docs/                         # Documentation
│   ├── api/                      # API reference
│   └── examples/                 # Usage examples
├── infrastructure/               # Docker configs
└── marketing/                    # Sales materials
```

## Component Details

### 1. Core Package (`src/core/`)

The foundation of all functionality.

#### encryption.py
- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key Generation:** Secure random using `secrets` module
- **Nonce:** 12-byte random nonce per encryption
- **Integrity:** SHA-256 checksum of original file
- **Key Storage:** Mode 600 (owner read/write only)

```python
# Encryption flow
Original → Nonce + AES-GCM(key, nonce, data) + Tag → Encrypted
```

#### config.py
- **Pattern:** Singleton settings object
- **Sources:** Environment variables, defaults
- **Validation:** Type checking, path validation

#### rate_limiter.py
- **Algorithm:** Token bucket
- **Purpose:** Prevent API abuse, cost control
- **Default:** 10 requests/second, 20 burst

### 2. Cloud Package (`src/cloud/`)

Multi-provider cloud storage with security.

#### Base Connector Pattern
All connectors inherit from `CloudConnector`:

```python
class CloudConnector(ABC):
    @abstractmethod
    def upload_file(self, local, remote): ...
    @abstractmethod
    def download_file(self, remote, local): ...
    @abstractmethod
    def delete_file(self, remote): ...
    @abstractmethod
    def list_files(self, prefix): ...
```

#### Security Features
- **Path Validation:** Prevents traversal attacks (`../`, `/etc/`)
- **Credential Cleanup:** Memory cleared on disconnect
- **Rate Limiting:** Prevents API abuse
- **Checksum Verification:** SHA-256 on upload/download

#### ConnectorManager
Unified interface for multi-cloud operations:
```python
manager.sync_file("file.enc", "backup.enc")  # Syncs to all registered clouds
```

### 3. Medical Package (`src/medical/`)

Healthcare-grade medical imaging.

#### DICOM Processing
- **Read:** Single files and series
- **Anonymize:** HIPAA-compliant PHI removal
- **Convert:** To PNG, NIfTI formats
- **Metadata:** Extract patient, study, series info

#### Preprocessing Pipeline
```
Raw MRI → Bias Correction → Denoising → Normalization → Preprocessed
```

#### U-Net Segmentation
Three architecture variants:
- **Standard:** Classic encoder-decoder
- **Attention:** With attention gates
- **Residual:** With skip connections

#### ML Inference
```
Input → Preprocess → Model → Postprocess → Result
         ↓           ↓
   BreastMRI     PyTorch/
   Preprocessor   ONNX
```

### 4. Processing Package (`src/processing/`)

GPU-accelerated media operations.

#### Device Detection
```
CUDA → ROCm → MPS → XPU → CPU
(NVIDIA) (AMD) (Apple) (Intel) (Fallback)
```

#### Operations
- Resize with interpolation
- Blur (Gaussian, Box)
- Sharpen (Unsharp mask)
- Edge detection (Sobel, Canny)

### 5. Licensing Package (`src/licensing/`)

Commercial license management.

#### License Tiers
| Tier | Features |
|------|----------|
| Free | Local encryption only |
| Pro | Cloud storage, GPU processing |
| Enterprise | Multi-cloud sync, priority support |

#### Validation
- HMAC-SHA256 signature verification
- Device activation tracking
- Expiration checking

### 6. CLI Package (`src/cli/`)

User-facing command interface.

#### Command Groups
```
smp
├── encrypt/decrypt     (crypto.py)
├── upload/download     (cloud.py)
├── resize/filter/info  (media.py)
├── license             (license.py)
│   ├── activate
│   ├── status
│   └── deactivate
└── medical             (medical.py)
    ├── dicom-info
    ├── anonymize
    ├── convert
    ├── preprocess
    ├── predict
    ├── segment
    └── evaluate
```

## Data Flow

### Encrypt & Upload Flow
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Input   │───►│ Encrypt  │───►│ Checksum │───►│  Upload  │
│  File    │    │AES-256-GCM│    │  SHA-256 │    │  Cloud   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Medical Analysis Flow
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  DICOM   │───►│Preprocess│───►│ Segment  │───►│ Predict  │
│  Input   │    │   MRI    │    │  U-Net   │    │  Cancer  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                       │              │
                                       ▼              ▼
                                  ┌─────────┐   ┌──────────┐
                                  │  Mask   │   │  Report  │
                                  │  Output │   │  Output  │
                                  └─────────┘   └──────────┘
```

## Security Architecture

### Defense in Depth
1. **Encryption at Rest:** AES-256-GCM before any storage
2. **Encryption in Transit:** HTTPS for all cloud APIs
3. **Key Management:** Secure storage, never in code
4. **Path Validation:** Prevents directory traversal
5. **Credential Cleanup:** Memory zeroed after use
6. **Rate Limiting:** Prevents abuse

### Zero-Knowledge Design
```
User Device                    Cloud Provider
     │                              │
     │  ┌─────────────────────┐     │
     │  │ Encrypt with        │     │
     ├──│ user's key          │     │
     │  │ (never leaves       │     │
     │  │  device)            │     │
     │  └─────────────────────┘     │
     │                              │
     │  Upload encrypted blob  ─────►
     │                              │
     │  (Provider cannot read)      │
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| Encryption | cryptography (OpenSSL) |
| CLI | Click |
| GPU | PyTorch (CUDA/ROCm/MPS) |
| Cloud SDKs | boto3, google-api, dropbox |
| Medical | pydicom, nibabel |
| ML | PyTorch, ONNX Runtime |
| Testing | pytest |

## Extension Points

### Adding a New Cloud Connector
1. Create `src/cloud/connectors/newcloud.py`
2. Inherit from `CloudConnector`
3. Implement abstract methods
4. Add path validation
5. Register in `ConnectorManager`

### Adding a New ML Model
1. Create model class in `src/medical/inference/`
2. Implement `predict()` method
3. Add to `CancerPredictionPipeline`
4. Add CLI command in `src/cli/medical.py`

### Adding a New Image Filter
1. Add method to `GPUMediaProcessor`
2. Handle GPU/CPU fallback
3. Add CLI command in `src/cli/media.py`

## Performance Considerations

### GPU Memory Management
- Tensors cleared after operations
- Batch processing for large datasets
- Automatic fallback to CPU

### Cloud Upload Optimization
- Checksum-based deduplication
- Parallel multi-part upload (S3)
- Connection pooling

### Medical Image Processing
- Streaming for large volumes
- Slice-by-slice inference
- Memory-efficient preprocessing
