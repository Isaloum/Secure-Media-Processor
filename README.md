# Secure Media Processor

**Privacy-focused media processing with GPU acceleration and cloud storage integration.**

## 🌟 Features

- 🔐 Military-Grade Encryption: AES-256-GCM encryption for all media files
- ☁️ Cloud Storage Integration: Seamless integration with AWS S3
- ⚡ GPU Acceleration: Lightning-fast image and video processing using CUDA
- 🔒 Privacy-First: All processing happens locally on your GPU
- 🛡️ Secure Deletion: Multi-pass secure file deletion
- 📦 Batch Processing: Process multiple files efficiently
- ✨ Image Filters: Blur, sharpen, edge detection, and more

## 📋 Requirements

- Python 3.8+
- NVIDIA GPU with CUDA support (optional, will fall back to CPU)
- AWS account for cloud storage (optional)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your cloud storage credentials
```

## 💻 Usage

### Encrypt a file:
```bash
python main.py encrypt input.jpg encrypted.bin
```

### Decrypt a file:
```bash
python main.py decrypt encrypted.bin output.jpg
```

### Upload to cloud storage:
```bash
python main.py upload encrypted.bin --remote-key media/image1.enc
```

### Download from cloud storage:
```bash
python main.py download media/image1.enc downloaded.bin
```

### Resize an image (GPU accelerated):
```bash
python main.py resize input.jpg output.jpg --width 1920 --height 1080
```

### Apply filters:
```bash
python main.py filter-image input.jpg output.jpg --filter blur --intensity 1.5
```

### Check system information:
```bash
python main.py info
```

## 🔐 Security Features

- AES-256-GCM: Industry-standard authenticated encryption
- Random Nonces: Each encryption uses a unique random nonce
- Secure Key Storage: Keys stored with restricted file permissions
- Checksum Verification: SHA-256 checksums for file integrity
- Secure Deletion: Multi-pass overwrite before deletion

## 📝 License

MIT License - feel free to use this project for your own purposes.

---

**Built with ❤️ for privacy-conscious users**