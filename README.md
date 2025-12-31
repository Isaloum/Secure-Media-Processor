# 🔐 Secure Media Processor

A privacy-focused, military-grade encryption tool for protecting your sensitive media files with AES-256-GCM encryption.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Encryption](https://img.shields.io/badge/encryption-AES--256--GCM-red.svg)

## ✨ Features

- 🔒 **Military-Grade Encryption**: AES-256-GCM encryption for maximum security
- ☁️ **Cloud Backup**: Seamless integration with AWS S3, Google Cloud Storage, and Azure
- 🚀 **GPU Acceleration**: Optional GPU support for faster processing (when PyTorch is available)
- 🖥️ **Cross-Platform**: Works on macOS, Linux, and Windows
- 📦 **Batch Operations**: Encrypt/decrypt multiple files at once
- 🔑 **Secure Key Management**: Automatic master key generation and storage
- 🛡️ **Zero-Knowledge**: Your encryption keys never leave your device

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

**Core Features (Encryption + Cloud Storage):**

```bash
# Clone the repository
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install -r requirements-core.txt
```

**Full Installation (With GPU Support):**

```bash
# Install all dependencies including PyTorch
pip install -r requirements.txt
```

### First Run

```bash
# Check installation
python main.py info
```

---

## 📚 Usage Examples

### Encrypt a File

```bash
python main.py encrypt secret.txt encrypted.bin
```

**Output:**
```
✓ File encrypted successfully!
  - Original size: 1024 bytes
  - Encrypted size: 1052 bytes
  - Algorithm: AES-256-GCM
```

### Decrypt a File

```bash
python main.py decrypt encrypted.bin decrypted.txt
```

### Upload to Cloud (AWS S3)

```bash
# Set environment variables in .env file
export AWS_BUCKET_NAME=my-secure-bucket
export AWS_REGION=us-east-1

# Upload encrypted file
python main.py upload encrypted.bin
```

### Download from Cloud

```bash
python main.py download encrypted.bin downloaded.bin --bucket my-secure-bucket
```

---

## 🔑 Security Features

### Encryption Algorithm

- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Size**: 256 bits (32 bytes)
- **Authentication**: Built-in authentication tag
- **Nonce**: Random 96-bit nonce per encryption

### Key Management

- Master key automatically generated on first run
- Stored at `./keys/master.key` with restricted permissions (0600)
- **⚠️ CRITICAL**: Backup your master key! Without it, encrypted files cannot be recovered

### Best Practices

✅ **DO:**
- Keep your master key in a secure location
- Use strong passwords for cloud storage credentials
- Encrypt files before uploading to cloud storage
- Regularly backup your encryption keys

❌ **DON'T:**
- Share your master key with anyone
- Store keys in public repositories
- Use the same key across multiple systems
- Upload unencrypted sensitive files to the cloud

---

## 🛠️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Encryption
MASTER_KEY_PATH=./keys/master.key

# AWS S3 Configuration
AWS_BUCKET_NAME=my-secure-bucket
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## 📋 Command Reference

| Command | Description |
|---------|-------------|
| `info` | Display system information |
| `encrypt <input> <output>` | Encrypt a file |
| `decrypt <input> <output>` | Decrypt a file |
| `upload <file>` | Upload file to cloud |
| `download <key> <output>` | Download file from cloud |

---

## 🐛 Troubleshooting

### "GPU processing not available (PyTorch not installed)"

**Solution:** This is normal! GPU processing is optional. The app works perfectly in CPU mode. To enable GPU features:

```bash
pip install torch torchvision
```

### "Permission denied" when accessing master key

**Solution:**
```bash
chmod 600 keys/master.key
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [cryptography](https://cryptography.io/) library
- Cloud storage powered by [boto3](https://boto3.amazonaws.com/)
- Optional GPU acceleration with [PyTorch](https://pytorch.org/)

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Isaloum/Secure-Media-Processor/discussions)

---

<p align="center">Made with ❤️ for privacy and security</p>
