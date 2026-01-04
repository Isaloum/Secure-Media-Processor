# Secure Media Processor

<div align="center">

**🔒 Professional-grade media processing with military-grade encryption, GPU acceleration, and multi-cloud storage integration**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Security: AES-256-GCM](https://img.shields.io/badge/security-AES--256--GCM-green.svg)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)
[![CI](https://github.com/Isaloum/Secure-Media-Processor/workflows/Python%20CI/badge.svg)](https://github.com/Isaloum/Secure-Media-Processor/actions)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/Isaloum/Secure-Media-Processor/actions)

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
```

4. **Configure credentials** (Required for cloud storage):
```bash
cp .env.example .env
# Edit .env with your cloud storage credentials
```

**Important:** Always use environment variables for credentials. Never hardcode sensitive information in your code. The `.env` file is already included in `.gitignore` to prevent accidental commits.

```bash
# Example .env configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=your-bucket-name

GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GCP_CREDENTIALS_PATH=path/to/credentials.json

DROPBOX_ACCESS_TOKEN=your_dropbox_access_token
```

5. **Set up logging** (Optional):
```python
from logging_config import setup_logging
import logging

# Development: detailed console + file logging
setup_logging(log_level=logging.DEBUG, log_file='logs/app.log')

# Production: warnings/errors only
setup_logging(log_level=logging.WARNING, log_file='/var/log/app.log')
```

See `logging_config.py` for more configuration options.

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
- ✅ Automated testing with pytest
- ✅ GitHub Actions CI/CD pipeline
- ✅ Comprehensive logging system

### Upcoming Features
- 🔲 **Video Processing**: GPU-accelerated video encoding/transcoding
- 🔲 **Azure Blob Storage**: Azure connector implementation
- 🔲 **End-to-End Encryption**: Zero-knowledge cloud storage
- 🔲 **Web Interface**: Browser-based UI for easier management
- 🔲 **Automated Backups**: Scheduled backup across multiple clouds
- 🔲 **File Versioning**: Track and restore previous file versions
- 🔲 **Compression**: Intelligent compression before encryption
- 🔲 **Docker Support**: Containerized deployment
- 🔲 **API Server**: RESTful API for programmatic access

## 🧪 Testing & Development

### Running Tests

The project includes comprehensive test coverage for all connectors and core functionality.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_s3_connector.py -v

# Run tests matching a pattern
pytest tests/ -k "connector" -v
```

### Linting and Code Quality

```bash
# Install linting tools
pip install flake8 black isort

# Check code style
flake8 src/ tests/

# Format code
black src/ tests/

# Sort imports
isort src/ tests/
```

### Contributing Tests

When contributing new features:
1. Write tests for all new functionality
2. Ensure all tests pass before submitting PR
3. Aim for >80% code coverage
4. Mock external dependencies (cloud APIs, etc.)

See existing tests in the `tests/` directory for examples.

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