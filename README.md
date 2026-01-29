# Secure Media Processor

<div align="center">

**A secure data pipeline for transferring sensitive data from cloud to local GPU processing**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Security: AES-256-GCM](https://img.shields.io/badge/security-AES--256--GCM-green.svg)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)
[![Tests](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml)
[![codecov](https://codecov.io/gh/Isaloum/Secure-Media-Processor/branch/main/graph/badge.svg)](https://codecov.io/gh/Isaloum/Secure-Media-Processor)
[![PyPI version](https://badge.fury.io/py/secure-media-processor.svg)](https://badge.fury.io/py/secure-media-processor)

</div>

---

## The Problem

You have sensitive data (medical images, confidential documents, research data) stored in the cloud. You need to process it on your local GPU workstation. **How do you transfer it securely?**

Traditional approaches leave data vulnerable:
- Cloud providers can access unencrypted data
- Data sits decrypted during processing
- No audit trail for compliance (HIPAA, GDPR)
- Sensitive files left on disk after processing

## The Solution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   [Hospital/Cloud]  ══════════════►  [Your GPU Workstation]                │
│                           │                                                 │
│                     ┌─────┴─────┐                                           │
│                     │ ENCRYPTED │                                           │
│                     │  SECURE   │                                           │
│                     │ PIPELINE  │                                           │
│                     └───────────┘                                           │
│                                                                             │
│   • Data encrypted BEFORE leaving source                                   │
│   • Keys NEVER leave your workstation                                      │
│   • Decryption ONLY on your local machine                                  │
│   • Audit trail for compliance                                             │
│   • Secure deletion after processing                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Secure Media Processor** is a secure pipeline that ensures sensitive data is protected at every stage—from cloud storage to local GPU processing and cleanup.

## Key Features

### End-to-End Encryption
- **AES-256-GCM** authenticated encryption
- **ECDH key exchange** for multi-party transfers
- **Zero-knowledge mode** — cloud provider never sees plaintext

### Multi-Cloud Support
- AWS S3
- Google Drive
- Dropbox
- Azure Blob Storage (coming soon)

### Compliance Ready
- **HIPAA/GDPR** compliant audit logging
- Immutable audit trail with cryptographic verification
- Configurable retention policies

### Secure by Default
- Multi-pass secure deletion (DoD 5220.22-M)
- Encrypted key storage
- Checksum verification on all transfers

## Quick Start

### Installation

```bash
pip install secure-media-processor
```

### Basic Usage

```python
from secure_media_processor import Pipeline, TransferMode

# Initialize secure pipeline
pipeline = Pipeline(
    encryption_key="~/.smp/keys/master.key",
    audit_log="~/.smp/audit/"
)

# Add your cloud source
pipeline.add_source('hospital', S3Connector(
    bucket_name='patient-scans',
    region='us-east-1'
))

# Secure download to local GPU workstation
manifest = pipeline.secure_download(
    source='hospital',
    remote_path='mri-scans/patient-001/',
    local_path='/secure/gpu-workspace/',
    mode=TransferMode.ZERO_KNOWLEDGE  # Maximum security
)

# Verify data integrity
assert pipeline.verify_integrity(manifest)

# Process locally on your GPU (your code here)
results = your_ml_model.process(manifest.destination)

# Secure cleanup when done
pipeline.secure_delete(manifest.destination)
```

## Who Is This For?

- **Medical researchers** processing patient MRI/CT scans
- **Healthcare organizations** meeting HIPAA requirements
- **Research institutions** handling sensitive data
- **Anyone** who needs to securely move data to GPU for processing

## Architecture

```
secure-media-processor/
├── src/
│   ├── core/                    # Core pipeline functionality
│   │   ├── secure_transfer.py   # Main transfer pipeline
│   │   ├── encryption.py        # AES-256-GCM encryption
│   │   ├── audit_logger.py      # Compliance logging
│   │   └── key_exchange.py      # ECDH key exchange
│   ├── connectors/              # Cloud storage connectors
│   │   ├── s3_connector.py
│   │   ├── google_drive_connector.py
│   │   └── dropbox_connector.py
│   └── cli.py                   # Command-line interface
├── plugins/                     # Optional processing plugins
│   └── smp_medical/             # Medical imaging plugin
└── docs/                        # Documentation
    ├── architecture/
    ├── api/
    └── examples/
```

## Plugin Architecture

The core package focuses on **secure data transfer**. Domain-specific processing is handled by optional plugins:

```bash
# Medical imaging (DICOM, U-Net segmentation)
pip install secure-media-processor[medical]

# Video processing (coming soon)
pip install secure-media-processor[video]
```

Plugins process data **locally** after it has been securely transferred.

## Documentation

- **[Security Model](docs/architecture/SECURITY_MODEL.md)** — Threat model, encryption details
- **[Data Flow](docs/architecture/DATA_FLOW.md)** — How data moves through the pipeline
- **[Pipeline API](docs/api/PIPELINE_API.md)** — Core API reference
- **[Examples](docs/examples/)** — Working code examples

## Security Model

| Stage | Protection |
|-------|------------|
| At rest (cloud) | AES-256-GCM encryption |
| In transit | AES-256-GCM + TLS |
| At rest (local) | Encrypted with master key |
| Processing | Decrypted only in memory |
| Cleanup | Multi-pass secure deletion |

**Zero-Knowledge Transfer**: In this mode, data is encrypted at the source (e.g., hospital) using a shared key derived via ECDH. The cloud provider **never** has access to the plaintext or decryption keys.

## Compliance

### HIPAA
- Audit logging with 6-year retention
- Access controls (local-only decryption)
- Encryption meets requirements

### GDPR
- Data minimization support
- Right to erasure (secure deletion)
- Complete audit trail

## CLI Usage

```bash
# Encrypt a file locally
smp encrypt sensitive-data.dcm encrypted.bin

# Download from cloud (decrypts locally)
smp download s3://bucket/path/file.enc ./local-file.dcm

# Secure delete
smp delete --secure ./sensitive-data.dcm

# View system info
smp info
```

## Roadmap

### Version 2.0 (Current Focus)
- [x] Core secure transfer pipeline
- [x] ECDH key exchange
- [x] HIPAA-compliant audit logging
- [x] Plugin architecture
- [ ] Streaming transfer for large files
- [ ] Azure Blob Storage connector

### Future
- [ ] Docker containerization
- [ ] REST API server
- [ ] Web dashboard
- [ ] Hardware Security Module (HSM) integration

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Priority areas:**
- Additional cloud connectors
- Performance optimization
- Security auditing

## Security

Security is the core mission. If you discover a vulnerability, please see our [Security Policy](SECURITY.md) for responsible disclosure.

## License

MIT License — see [LICENSE](LICENSE).

---

<div align="center">

**Secure Media Processor** — *Your data, your GPU, your control.*

Built for researchers who need security without compromise.

</div>
