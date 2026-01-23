#!/bin/bash
# Deploy hero section fix to GitHub Pages
# This script removes the duplicate custom hero div from gh-pages

set -e

echo "🔧 Deploying hero section fix to gh-pages..."

# Save current branch
CURRENT_BRANCH=$(git branch --show-current)

# Switch to gh-pages and get latest
git fetch origin gh-pages
git checkout gh-pages
git reset --hard origin/gh-pages

# Update index.md to remove duplicate hero
cat > index.md << 'INDEXMD'
---
layout: default
title: Secure Media Processor - Privacy-First Media Encryption & Cloud Storage
description: Military-grade encryption meets GPU acceleration for your media files
---

<div align="center" style="margin: 40px 0;">
  <img src="https://img.shields.io/github/stars/Isaloum/Secure-Media-Processor?style=for-the-badge&logo=github&color=gold" alt="GitHub Stars">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/github/actions/workflow/status/Isaloum/Secure-Media-Processor/python-tests.yml?style=for-the-badge&logo=github-actions&label=tests" alt="Tests">
  <img src="https://img.shields.io/codecov/c/github/Isaloum/Secure-Media-Processor?style=for-the-badge&logo=codecov" alt="Coverage">
</div>

---

## 🎯 What is Secure Media Processor?

**Enterprise-grade media security in your hands.** Process, encrypt, and store your sensitive photos and videos across multiple cloud providers with complete privacy control. All encryption happens locally—your data stays yours.

Perfect for photographers, content creators, privacy advocates, and enterprises requiring secure media workflows.

---

## ✨ Key Features

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 30px; margin: 40px 0;">

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>🔐 Military-Grade Encryption</h3>
  <p><strong>AES-256-GCM</strong> authenticated encryption ensures your files are protected with the same technology used by governments and financial institutions.</p>
  <ul>
    <li>✓ Local encryption (zero trust)</li>
    <li>✓ SHA-256 integrity verification</li>
    <li>✓ Secure key management</li>
  </ul>
</div>

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>☁️ Multi-Cloud Support</h3>
  <p>Store encrypted files across multiple cloud providers with a unified interface. Switch providers without changing your workflow.</p>
  <ul>
    <li>✓ AWS S3</li>
    <li>✓ Google Drive</li>
    <li>✓ Dropbox</li>
  </ul>
</div>

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>⚡ GPU Acceleration</h3>
  <p>Blazing-fast image processing powered by CUDA. Resize, filter, and transform images at incredible speeds.</p>
  <ul>
    <li>✓ CUDA support</li>
    <li>✓ CPU fallback</li>
    <li>✓ Batch processing</li>
  </ul>
</div>

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>🛡️ Privacy First</h3>
  <p>Zero-knowledge architecture means cloud providers never see your unencrypted data. You control the keys, you control the data.</p>
  <ul>
    <li>✓ No plaintext uploads</li>
    <li>✓ Local-only decryption</li>
    <li>✓ Secure deletion</li>
  </ul>
</div>

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>🧪 Production Ready</h3>
  <p>Comprehensive test suite with 45 automated tests and 66% code coverage. Battle-tested and ready for production use.</p>
  <ul>
    <li>✓ 45 automated tests</li>
    <li>✓ CI/CD pipeline</li>
    <li>✓ Type-safe codebase</li>
  </ul>
</div>

<div style="padding: 25px; border: 2px solid #667eea; border-radius: 12px; background: #f8f9ff;">
  <h3>👨‍💻 Developer Friendly</h3>
  <p>Clean architecture, comprehensive docs, and easy extensibility. Add new cloud connectors in minutes.</p>
  <ul>
    <li>✓ Modular design</li>
    <li>✓ Full documentation</li>
    <li>✓ Plugin architecture</li>
  </ul>
</div>

</div>

---

## 🚀 Quick Start {#get-started}

### Installation

\`\`\`bash
# Install from PyPI
pip install secure-media-processor

# Or install from source
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor
pip install -e .
\`\`\`

### Basic Usage

\`\`\`bash
# Encrypt a file
smp encrypt photo.jpg --output photo.enc

# Upload to cloud (encrypted)
smp upload photo.enc --provider s3 --bucket my-secure-bucket

# Download and decrypt
smp download photo.enc --output photo_decrypted.jpg
smp decrypt photo_decrypted.jpg
\`\`\`

### GPU-Accelerated Processing

\`\`\`bash
# Resize image with GPU acceleration
smp resize image.jpg --width 1920 --height 1080 --gpu

# Apply filters
smp filter image.jpg --type blur --intensity 5 --gpu
\`\`\`

---

## 📊 Use Cases

### For Photographers
- Encrypt client photos before cloud backup
- GPU-accelerated batch processing
- Maintain EXIF data integrity

### For Content Creators
- Secure work-in-progress uploads
- Multi-cloud redundancy
- Fast processing pipelines

### For Enterprises
- Compliance with data protection regulations
- Zero-knowledge cloud storage
- Audit trails and access logs

### For Privacy Advocates
- True end-to-end encryption
- No plaintext cloud exposure
- Local key management

---

## 🔒 Security Features

### Encryption Details
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2-HMAC-SHA256
- **Authentication**: Built-in authenticated encryption
- **Integrity**: SHA-256 checksums for all files

### Security Best Practices
- Keys never leave your machine
- Secure key storage with file permissions (0600)
- Memory-safe credential handling
- 3-pass secure file deletion

---

## 🛠️ Advanced Features

### Cloud Connector API
Easily add support for new cloud providers:

\`\`\`python
from secure_media_processor.connectors import CloudConnector

class MyCloudConnector(CloudConnector):
    def upload_file(self, local_path, remote_path):
        # Your implementation here
        pass
\`\`\`

### Batch Processing
Process multiple files efficiently:

\`\`\`bash
# Encrypt and upload entire directory
smp batch-upload photos/ --provider gdrive --folder "Encrypted Photos"
\`\`\`

### License Management
Unlock Pro features with a license key:

\`\`\`bash
# Activate Pro license
smp license activate YOUR-LICENSE-KEY --email you@example.com

# Check license status
smp license status
\`\`\`

---

## 📈 Performance

| Operation | CPU | GPU (CUDA) | Speedup |
|-----------|-----|------------|---------|
| Resize 4K image | 450ms | 45ms | 10x |
| Batch encrypt (100 files) | 12s | 3s | 4x |
| Apply filters | 890ms | 95ms | 9.4x |

*Benchmarks on Intel i7 + NVIDIA RTX 3080*

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

\`\`\`bash
# Clone the repo
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ --cov=src

# Run linting
black src/ tests/
flake8 src/ tests/
\`\`\`

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 💡 Support

- **Documentation**: [Full docs](https://secure-media-processor.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Isaloum/Secure-Media-Processor/discussions)
- **Email**: support@secure-media-processor.com

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Isaloum/Secure-Media-Processor&type=Date)](https://star-history.com/#Isaloum/Secure-Media-Processor&Date)

---

<div align="center">
  <p><strong>Built with ❤️ for privacy and security</strong></p>
  <p>© 2024 Secure Media Processor. All rights reserved.</p>
</div>
INDEXMD

# Commit the change
git add index.md
git commit -m "Fix: Remove duplicate hero section for professional look

- Removed custom hero div that duplicated theme's hero
- Added 'description' field to YAML front matter
- Theme now generates single, clean hero automatically
- Professional single hero section instead of duplicate"

# Push to gh-pages
echo "📤 Pushing to gh-pages..."
git push origin gh-pages

# Return to original branch
git checkout "$CURRENT_BRANCH"

echo "✅ Done! GitHub Pages will rebuild in 1-2 minutes."
echo "🌐 Visit: https://isaloum.github.io/Secure-Media-Processor/"
echo "🔄 Hard refresh with: Cmd + Shift + R"
