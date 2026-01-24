# Getting Started with Secure Media Processor

Welcome! This guide will help you get started with Secure Media Processor, even if you've never used the command line or worked with encryption before.

## 📖 Table of Contents

- [What is Secure Media Processor?](#what-is-secure-media-processor)
- [Why Use It?](#why-use-it)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Your First Steps](#your-first-steps)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## What is Secure Media Processor?

Secure Media Processor is a tool that helps you:
- **Encrypt** (lock) your photos and videos so only you can access them
- **Store** encrypted files safely in the cloud (like Dropbox, Google Drive, or Amazon S3)
- **Process** images faster using your computer's graphics card (GPU)
- **Protect** your privacy by doing all encryption on your own computer

Think of it as a digital safe for your media files that you control completely.

## Why Use It?

### Privacy
All encryption happens on **your computer**, not in the cloud. This means:
- Cloud providers never see your unencrypted files
- Only you have the keys to unlock your files
- Your data stays private even if cloud storage is compromised

### Flexibility
- Store files in multiple cloud services simultaneously
- Switch between cloud providers without changing your workflow
- Process images faster with GPU acceleration

### Security
- Military-grade encryption (AES-256-GCM)
- Each file is verified to ensure it wasn't corrupted
- Secure deletion removes files completely

## Prerequisites

### What You'll Need

1. **A Computer** with:
   - Windows, macOS, or Linux
   - At least 4GB of RAM
   - 500MB of free disk space

2. **Python 3.8 or newer** installed on your computer
   - Check if you have it: Open a terminal/command prompt and type `python --version`
   - Don't have it? Download from [python.org](https://www.python.org/downloads/)

3. **Optional: Cloud Storage Account**
   - Amazon Web Services (AWS) S3
   - Google Drive (via Google Cloud)
   - Dropbox
   - *Not required for local encryption/decryption*

4. **Optional: NVIDIA Graphics Card**
   - Only needed for GPU-accelerated image processing
   - The program works fine without it, just a bit slower

## Installation

Follow these steps carefully:

### Step 1: Download the Project

**Option A: Using Git (Recommended)**
```bash
git clone https://github.com/Isaloum/Secure-Media-Processor.git
cd Secure-Media-Processor
```

**Option B: Download ZIP**
1. Go to [https://github.com/Isaloum/Secure-Media-Processor](https://github.com/Isaloum/Secure-Media-Processor)
2. Click the green "Code" button
3. Click "Download ZIP"
4. Extract the ZIP file
5. Open a terminal/command prompt in the extracted folder

### Step 2: Create a Virtual Environment

A virtual environment keeps this project's files separate from other Python projects.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You'll know it worked when you see `(venv)` at the start of your command line.

### Step 3: Install Dependencies

This downloads all the required libraries:
```bash
pip install -r requirements.txt
```

**Optional - GPU Acceleration**: If you want GPU support for faster processing:
```bash
pip install -r requirements-gpu.txt
# Or use: pip install -e .[gpu]
```

Wait for the installation to complete (this may take a few minutes).

### Step 4: Set Up Configuration (Optional)

If you plan to use cloud storage:

1. Copy the example configuration file:
```bash
cp .env.example .env
```

2. Open `.env` in a text editor

3. Fill in your cloud credentials (see "Cloud Setup" section below)

## Your First Steps

Let's encrypt your first file!

### Test 1: Encrypt a File

1. Place a photo or document in the project folder (e.g., `my-photo.jpg`)

2. Run the encryption command:
```bash
python main.py encrypt my-photo.jpg encrypted-photo.bin
```

3. You should see a success message and a new file `encrypted-photo.bin`

**What happened?** Your photo was encrypted with a strong password and saved as `encrypted-photo.bin`. The original file is unchanged.

### Test 2: Decrypt the File

Now let's get your photo back:
```bash
python main.py decrypt encrypted-photo.bin recovered-photo.jpg
```

**What happened?** The encrypted file was decrypted back to its original form. Open `recovered-photo.jpg` to verify it matches your original!

### Test 3: Check System Information

See if GPU acceleration is available:
```bash
python main.py info
```

This shows:
- Whether you have a GPU available
- How much memory your GPU has
- Your system configuration

## Common Tasks

### Task 1: Resize an Image

Make an image smaller or larger:
```bash
python main.py resize my-photo.jpg resized-photo.jpg --width 1920 --height 1080
```

This creates a new image sized to 1920x1080 pixels.

### Task 2: Apply Filters

#### Blur an Image
```bash
python main.py filter-image my-photo.jpg blurred.jpg --filter blur --intensity 1.5
```

#### Sharpen an Image
```bash
python main.py filter-image my-photo.jpg sharpened.jpg --filter sharpen --intensity 2.0
```

#### Edge Detection
```bash
python main.py filter-image my-photo.jpg edges.jpg --filter edge
```

### Task 3: Upload to Cloud Storage

**Prerequisites:** You must have configured cloud credentials in `.env`

```bash
# Encrypt first
python main.py encrypt my-photo.jpg encrypted-photo.bin

# Upload to cloud
python main.py upload encrypted-photo.bin --remote-key photos/my-photo.enc
```

The file is now stored securely in your cloud storage!

### Task 4: Download from Cloud

```bash
# Download encrypted file
python main.py download photos/my-photo.enc downloaded.bin

# Decrypt it
python main.py decrypt downloaded.bin recovered-photo.jpg
```

## Cloud Setup Guide

### Setting Up AWS S3

1. **Create an AWS Account** at [aws.amazon.com](https://aws.amazon.com)

2. **Create an S3 Bucket:**
   - Go to S3 console
   - Click "Create bucket"
   - Choose a unique name and region
   - Keep default settings for security

3. **Create Access Keys:**
   - Go to IAM console
   - Create a new user with S3 access
   - Generate access keys
   - Copy the Access Key ID and Secret Access Key

4. **Update `.env`:**
```
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your-bucket-name
```

### Setting Up Google Drive

1. **Create a Google Cloud Project** at [console.cloud.google.com](https://console.cloud.google.com)

2. **Enable Google Drive API:**
   - Go to APIs & Services
   - Click "Enable APIs and Services"
   - Search for "Google Drive API"
   - Click Enable

3. **Create Service Account:**
   - Go to IAM & Admin > Service Accounts
   - Create a service account
   - Download the JSON key file

4. **Update `.env`:**
```
GCP_CREDENTIALS_PATH=/path/to/your/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

### Setting Up Dropbox

1. **Create a Dropbox Account** at [dropbox.com](https://www.dropbox.com)

2. **Create an App:**
   - Go to [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
   - Click "Create app"
   - Choose "Scoped access"
   - Choose "Full Dropbox" access
   - Name your app

3. **Generate Access Token:**
   - In your app settings, find "OAuth 2"
   - Click "Generate access token"
   - Copy the token

4. **Update `.env`:**
```
DROPBOX_ACCESS_TOKEN=your_token_here
DROPBOX_ROOT_PATH=/SecureMedia
```

## Troubleshooting

### Problem: "Python not found"
**Solution:** Install Python from [python.org](https://www.python.org/downloads/) and make sure to check "Add Python to PATH" during installation.

### Problem: "Permission denied" when creating encryption keys
**Solution:** Make sure you have write permissions in the project folder. On macOS/Linux, you might need to run `chmod +x` on the script.

### Problem: GPU not detected but I have an NVIDIA card
**Solution:**
1. First, install GPU dependencies: `pip install -r requirements-gpu.txt` or `pip install -e .[gpu]`
2. Install NVIDIA CUDA drivers from [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)
3. If needed, reinstall PyTorch with CUDA support: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

### Problem: "Module not found" errors
**Solution:** Make sure you activated the virtual environment and ran `pip install -r requirements.txt`. For GPU support, also run `pip install -r requirements-gpu.txt`

### Problem: Cloud upload fails
**Solution:** 
1. Verify your credentials in `.env` are correct
2. Check that your bucket/folder exists
3. Ensure you have internet connectivity
4. Check cloud service status pages for outages

### Problem: File decryption fails
**Solution:** 
1. Make sure you're using the same encryption key that was used to encrypt
2. Verify the encrypted file wasn't corrupted (check file size isn't 0)
3. Don't rename or modify the `.key` file in the `keys/` folder

## Next Steps

Now that you're familiar with the basics:

1. **Read the full [README.md](README.md)** for advanced features
2. **Check out [CONTRIBUTING.md](CONTRIBUTING.md)** if you want to help improve the project
3. **Review [SECURITY.md](SECURITY.md)** for security best practices
4. **Explore the code** in the `src/` folder to understand how it works

## Tips for Safe Usage

1. **Backup Your Encryption Keys**: The files in `keys/` folder are critical. Back them up securely!
2. **Test First**: Always test encryption/decryption with non-critical files first
3. **Keep Originals**: Don't delete original files until you've verified encryption works
4. **Use Strong Passwords**: If adding password protection, use strong, unique passwords
5. **Regular Updates**: Keep the software updated for latest security fixes

## Getting Help

- **Questions?** Open a [GitHub Discussion](https://github.com/Isaloum/Secure-Media-Processor/discussions)
- **Found a bug?** Report it in [GitHub Issues](https://github.com/Isaloum/Secure-Media-Processor/issues)
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Welcome to secure media management! You're now in control of your privacy.** 🔒✨
