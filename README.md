# Secure Media Processor

<div align="center">

**🔒 Professional-grade media processing with military-grade encryption, GPU acceleration, and multi-cloud storage integration**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Security: AES-256-GCM](https://img.shields.io/badge/security-AES--256--GCM-green.svg)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)
[![Tests](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Isaloum/Secure-Media-Processor/actions/workflows/python-tests.yml)
[![codecov](https://codecov.io/gh/Isaloum/Secure-Media-Processor/branch/main/graph/badge.svg)](https://codecov.io/gh/Isaloum/Secure-Media-Processor)

*Privacy-first • GPU-accelerated • Cloud-ready • Production-tested*

</div>

---

## 🌟 Overview

Secure Media Processor is a production-ready, enterprise-grade solution for securely processing, encrypting, and storing media files across multiple cloud providers. Built with privacy and security as core principles, it offers seamless integration with AWS S3, Google Drive, and Dropbox, while maintaining complete local control over your data.

### Why Choose Secure Media Processor?

- ✅ **Zero-Trust Architecture**: All encryption happens locally before cloud upload
- ✅ **Plug-and-Play Cloud Connectors**: Switch between S3, Google Drive, and Dropbox effortlessly
- ✅ **Production-Ready**: Modular design, comprehensive error handling, and extensive logging
- ✅ **Performance-Optimized**: GPU-accelerated processing for blazing-fast operations
- ✅ **Developer-Friendly**: Clean API, comprehensive documentation, and extensible architecture

## ✨ Key Features

### 🔐 Security & Privacy
- **Military-Grade Encryption**: AES-256-GCM authenticated encryption
- **Local Processing**: All sensitive operations happen on your machine
- **Secure Key Management**: Protected key storage with restricted permissions
- **Integrity Verification**: SHA-256 checksums ensure data integrity
- **Secure Deletion**: Multi-pass overwrite before file removal

### ☁️ Multi-Cloud Storage
- **AWS S3**: Full S3 integration with server-side encryption
- **Google Drive**: Native Google Drive API support
- **Dropbox**: Seamless Dropbox integration
- **Unified Interface**: Switch providers without changing your code
- **Connector Manager**: Manage multiple cloud connections simultaneously

### ⚡ High-Performance Processing
- **GPU Acceleration**: CUDA-powered image and video processing
- **Batch Operations**: Process multiple files efficiently
- **Smart Fallback**: Automatic CPU fallback when GPU unavailable
- **Optimized Pipelines**: Minimal overhead, maximum throughput

### 🛠️ Developer Experience
- **Modular Architecture**: Clean separation of concerns
- **Extensible Design**: Easy to add new cloud providers or features
- **Comprehensive Logging**: Track every operation for debugging and auditing
- **Type Hints**: Full type annotations for better IDE support
- **Well-Documented**: Inline documentation and usage examples

## 📋 Requirements

- **Python**: 3.8 or higher
- **GPU** (Optional): NVIDIA GPU with CUDA support for accelerated processing
- **Cloud Accounts** (Optional): AWS, Google Cloud, or Dropbox accounts for cloud storage

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt

# Optional: For GPU acceleration support (NVIDIA/AMD/Apple/Intel)
pip install -r requirements-gpu.txt
# Or install via: pip install -e .[gpu]
```

4. **Configure credentials**:
```bash
cp .env.example .env
# Edit .env with your cloud storage credentials
```

### Basic Usage

#### Encrypt and Upload to Cloud
```bash
# Encrypt a file
python main.py encrypt my-photo.jpg encrypted-photo.bin

# Upload to S3
python main.py upload encrypted-photo.bin --remote-key secure/photo.enc
```

#### Download and Decrypt
```bash
# Download from cloud
python main.py download secure/photo.enc downloaded.bin

# Decrypt the file
python main.py decrypt downloaded.bin recovered-photo.jpg
```

#### GPU-Accelerated Image Processing
```bash
# Resize image with GPU acceleration
python main.py resize photo.jpg resized.jpg --width 1920 --height 1080

# Apply filters
python main.py filter-image photo.jpg filtered.jpg --filter blur --intensity 1.5
```

#### System Information
```bash
# Check GPU availability and system info
python main.py info
```

## 📚 Documentation

- **[Getting Started Guide](GETTING_STARTED.md)** - Step-by-step tutorial for beginners
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to this project
- **[Security Policy](SECURITY.md)** - Security best practices and reporting vulnerabilities

## 🏗️ Architecture

### Project Structure
```
Secure-Media-Processor/
├── src/
│   ├── connectors/          # Cloud storage connectors
│   │   ├── base_connector.py       # Abstract base class
│   │   ├── s3_connector.py         # AWS S3 implementation
│   │   ├── google_drive_connector.py  # Google Drive implementation
│   │   ├── dropbox_connector.py    # Dropbox implementation
│   │   └── connector_manager.py    # Multi-connector management
│   ├── encryption.py        # Encryption/decryption logic
│   ├── gpu_processor.py     # GPU-accelerated media processing
│   ├── cloud_storage.py     # Legacy cloud storage (S3)
│   ├── config.py           # Configuration management
│   └── cli.py              # Command-line interface
├── tests/                  # Test suite
├── main.py                 # Application entry point
└── requirements.txt        # Python dependencies
```

### Cloud Connector Design

The modular connector architecture allows seamless integration with multiple cloud providers:

```python
from src.connectors import ConnectorManager, S3Connector, DropboxConnector

# Initialize connector manager
manager = ConnectorManager()

# Add connectors
manager.add_connector('s3', S3Connector(
    bucket_name='my-bucket',
    region='us-east-1'
))
manager.add_connector('dropbox', DropboxConnector(
    access_token='your-token'
))

# Connect all providers
manager.connect_all()

# Upload to active connector
manager.upload_file('file.txt', 'remote/file.txt')

# Upload to specific provider
manager.upload_file('file.txt', 'file.txt', connector_name='dropbox')

# Sync file across multiple clouds
manager.sync_file_across_connectors(
    'important.txt',
    source_connector='s3',
    target_connectors=['dropbox', 'gdrive']
)
```

## 🧪 Testing & CI/CD

### Test Suite

The project includes comprehensive automated tests for all cloud connectors with 66% overall code coverage:

```bash
# Run all cloud connector tests
pytest tests/test_dropbox_connector.py tests/test_s3_connector_new.py tests/test_google_drive_connector_new.py -v

# Run with coverage reporting
pytest tests/ --cov=src/connectors --cov-report=term-missing
```

**Coverage Metrics**:
- S3 Connector: 87%
- Google Drive Connector: 82%
- Dropbox Connector: 65%
- Overall: 66%

### Testing Strategy

All connector tests use **global mocking fixtures** for consistent, isolated testing:

- **Dropbox**: `mock_dbx_global` fixture mocks `dropbox.Dropbox` class
- **S3**: `mock_s3_client_global` and `mock_s3_resource_global` fixtures mock `boto3.client()` and `boto3.resource()`
- **Google Drive**: `mock_gdrive_service_global` fixture mocks `googleapiclient.discovery.build()`

This approach ensures:
- No actual cloud API calls during testing
- Fast test execution (all 45 tests run in ~1 second)
- Predictable test behavior without external dependencies
- Easy debugging with controlled mock responses

### Continuous Integration

Every push and pull request triggers automated testing via GitHub Actions:

**Workflow**: [`.github/workflows/python-tests.yml`](.github/workflows/python-tests.yml)

**Pipeline Steps**:
1. **Environment Setup**: Python 3.11, install dependencies
2. **Test Execution**: Run all connector tests with verbose output
3. **Coverage Analysis**: Generate coverage reports (XML + terminal)
4. **Coverage Upload**: Publish to Codecov with `connector-tests` flag

**View CI Status**: All workflow runs are visible in the [Actions tab](https://github.com/Isaloum/Secure-Media-Processor/actions)

### Adding New Connector Tests

To add tests for a new connector:

1. Create `tests/test_<connector>_connector.py`
2. Add a global fixture using `autouse=True` and `scope="function"`
3. Mock the SDK/API constructor using `monkeypatch.setattr()`
4. Write tests using the global mock with `reset_mock()` between tests
5. Update CI workflow to include your test file

Example template:
```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_sdk_global(monkeypatch):
    """Global mock for SDK client"""
    mock = MagicMock()
    monkeypatch.setattr('sdk_module.Client', lambda *args, **kwargs: mock)
    yield mock
    mock.reset_mock()

def test_upload(mock_sdk_global):
    connector = MyConnector()
    connector.upload_file('test.txt', 'remote.txt')
    assert mock_sdk_global.upload.called
```

## 🔒 Security Workflow

1. **Local Encryption**: Files are encrypted on your machine using AES-256-GCM
2. **Checksum Generation**: SHA-256 hash calculated for integrity verification
3. **Secure Upload**: Encrypted data transmitted to cloud with TLS
4. **Server-Side Encryption**: Additional encryption layer at cloud provider
5. **Integrity Verification**: Checksum verified on download
6. **Secure Decryption**: Files decrypted only on your local machine

## 🗺️ Roadmap

### Current Version (v1.0)
- ✅ AES-256-GCM encryption
- ✅ Multi-cloud connectors (S3, Google Drive, Dropbox)
- ✅ GPU-accelerated image processing
- ✅ Comprehensive CLI interface

### Upcoming Features
- 🔲 **Video Processing**: GPU-accelerated video encoding/transcoding
- 🔲 **Azure Blob Storage**: Azure connector implementation
- 🔲 **End-to-End Encryption**: Zero-knowledge cloud storage
- 🔲 **Web Interface**: Browser-based UI for easier management
- 🔲 **Automated Backups**: Scheduled backup across multiple clouds
- 🔲 **File Versioning**: Track and restore previous file versions
- 🔲 **Compression**: Intelligent compression before encryption
- 🔲 **CI/CD Pipeline**: Automated testing and deployment
- 🔲 **Docker Support**: Containerized deployment
- 🔲 **API Server**: RESTful API for programmatic access

## 🤝 Contributing

We welcome contributions! Whether you're fixing bugs, improving documentation, or adding new features, your help makes this project better.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔐 Security

Security is our top priority. If you discover a security vulnerability, please see our [Security Policy](SECURITY.md) for responsible disclosure guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ for privacy-conscious users
- Inspired by the need for secure, cross-platform media management
- Special thanks to all contributors and the open-source community

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Isaloum/Secure-Media-Processor/discussions)
- **Documentation**: [Project Wiki](https://github.com/Isaloum/Secure-Media-Processor/wiki)

---

<div align="center">

**⭐ If you find this project useful, please consider giving it a star! ⭐**

*Secure Media Processor - Your privacy, your control, your cloud.*

</div>