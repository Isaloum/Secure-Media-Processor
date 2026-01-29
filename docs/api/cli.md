# CLI Reference

Command-line interface for Secure Media Processor.

## Installation

```bash
pip install secure-media-processor
```

## Usage

```bash
smp [OPTIONS] COMMAND [ARGS]...
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message |

---

## Commands Overview

| Command | Description |
|---------|-------------|
| `encrypt` | Encrypt a media file |
| `decrypt` | Decrypt a media file |
| `upload` | Upload to cloud storage |
| `download` | Download from cloud storage |
| `resize` | Resize an image |
| `filter` | Apply image filters |
| `info` | Show system/GPU info |
| `license` | License management |
| `medical` | Medical imaging tools |

---

## Encryption Commands

### encrypt

Encrypt a file using AES-256-GCM.

```bash
smp encrypt INPUT_FILE OUTPUT_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--key-path PATH` | Path to encryption key |

**Example:**
```bash
smp encrypt photo.jpg photo.enc
smp encrypt photo.jpg photo.enc --key-path ~/.smp/custom.key
```

### decrypt

Decrypt an encrypted file.

```bash
smp decrypt INPUT_FILE OUTPUT_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--key-path PATH` | Path to encryption key |

**Example:**
```bash
smp decrypt photo.enc photo_restored.jpg
```

---

## Cloud Commands

### upload

Upload a file to cloud storage. *Requires Pro or Enterprise license.*

```bash
smp upload LOCAL_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--remote-key TEXT` | Remote object key/path |
| `--bucket TEXT` | S3 bucket name |

**Example:**
```bash
smp upload backup.enc --bucket my-bucket --remote-key backups/2024/backup.enc
```

### download

Download a file from cloud storage. *Requires Pro or Enterprise license.*

```bash
smp download REMOTE_KEY LOCAL_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bucket TEXT` | S3 bucket name |
| `--verify / --no-verify` | Verify checksum (default: yes) |

**Example:**
```bash
smp download backups/file.enc restored.enc --bucket my-bucket
```

---

## Media Processing Commands

### resize

Resize an image. *GPU requires Pro or Enterprise license.*

```bash
smp resize INPUT_FILE OUTPUT_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--width INT` | Target width (required) |
| `--height INT` | Target height (required) |
| `--gpu / --no-gpu` | Use GPU acceleration (default: yes) |

**Example:**
```bash
smp resize photo.jpg thumbnail.jpg --width 200 --height 200
smp resize photo.jpg thumbnail.jpg --width 200 --height 200 --no-gpu
```

### filter

Apply filters to an image. *GPU requires Pro or Enterprise license.*

```bash
smp filter INPUT_FILE OUTPUT_FILE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--filter [blur\|sharpen\|edge]` | Filter type (default: blur) |
| `--intensity FLOAT` | Filter intensity (default: 1.0) |
| `--gpu / --no-gpu` | Use GPU acceleration (default: yes) |

**Example:**
```bash
smp filter photo.jpg blurred.jpg --filter blur --intensity 1.5
smp filter photo.jpg edges.jpg --filter edge
```

### info

Display system and GPU information.

```bash
smp info
```

**Output:**
```
📊 System Information

Device: CUDA
Name: NVIDIA GeForce RTX 3080
Total Memory: 10.00 GB
Allocated Memory: 0.50 GB
CUDA Version: 11.8
```

---

## License Commands

### license activate

Activate a license key.

```bash
smp license activate LICENSE_KEY [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--email TEXT` | Your email address (will prompt) |

**Example:**
```bash
smp license activate SMP-PRO-XXXX-XXXX-XXXX --email user@example.com
```

### license status

Show current license status.

```bash
smp license status
```

**Output:**
```
📋 License Status

Status: ✓ Active
Type: PRO
Email: user@example.com
Expires: 365 days
Devices: 1/3

Enabled Features:
  ✓ Cloud Storage
  ✓ Gpu Processing
  ✓ Batch Operations
```

### license deactivate

Deactivate license on this device.

```bash
smp license deactivate
```

---

## Medical Commands

### medical dicom-info

Display DICOM file or series information.

```bash
smp medical dicom-info PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--series` | List all series in directory |

**Example:**
```bash
smp medical dicom-info scan.dcm
smp medical dicom-info ./scans/ --series
```

### medical anonymize

Anonymize DICOM file for HIPAA compliance.

```bash
smp medical anonymize INPUT_PATH OUTPUT_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--keep-uids` | Keep original study/series UIDs |

**Example:**
```bash
smp medical anonymize patient.dcm anonymous.dcm
```

### medical convert

Convert DICOM to other formats.

```bash
smp medical convert INPUT_PATH OUTPUT_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format [png\|nifti]` | Output format (default: png) |
| `--window-center FLOAT` | Window center for contrast |
| `--window-width FLOAT` | Window width for contrast |

**Example:**
```bash
smp medical convert scan.dcm scan.png
smp medical convert ./series/ volume.nii.gz --format nifti
```

### medical preprocess

Preprocess medical image for ML analysis.

```bash
smp medical preprocess INPUT_PATH OUTPUT_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--bias-correction / --no-bias-correction` | N4 bias correction (default: yes) |
| `--denoise / --no-denoise` | Noise reduction (default: yes) |
| `--normalize [zscore\|minmax\|percentile]` | Normalization (default: zscore) |
| `--enhance-contrast` | CLAHE contrast enhancement |

**Example:**
```bash
smp medical preprocess scan.dcm preprocessed.npy --normalize zscore
```

### medical predict

Run cancer prediction on MRI.

```bash
smp medical predict INPUT_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--model PATH` | Path to trained model (required) |
| `--model-type [pytorch\|onnx\|torchscript]` | Model type (default: pytorch) |
| `--gpu / --no-gpu` | Use GPU (default: yes) |
| `--generate-heatmap` | Generate attention heatmap |
| `--output-report PATH` | Save report to file |

**Example:**
```bash
smp medical predict scan.dcm --model cancer_model.pt
smp medical predict ./series/ --model model.onnx --model-type onnx --output-report report.txt
```

### medical segment

Run U-Net segmentation for tumor detection.

```bash
smp medical segment INPUT_PATH OUTPUT_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--model PATH` | Path to trained U-Net model |
| `--variant [standard\|attention\|residual]` | Architecture (default: standard) |
| `--threshold FLOAT` | Binary threshold 0-1 (default: 0.5) |
| `--gpu / --no-gpu` | Use GPU (default: yes) |
| `--save-probability` | Save probability map |
| `--output-format [png\|npy\|both]` | Output format (default: png) |

**Example:**
```bash
smp medical segment mri.dcm mask.png --model unet.pt --variant attention
smp medical segment ./volume/ mask.npy --output-format npy --save-probability
```

### medical evaluate

Evaluate segmentation against ground truth.

```bash
smp medical evaluate PREDICTION_PATH GROUND_TRUTH_PATH [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--surface-metrics` | Include Hausdorff distance |

**Example:**
```bash
smp medical evaluate prediction.png ground_truth.png --surface-metrics
```

### medical info

Display medical imaging dependencies and capabilities.

```bash
smp medical info
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SMP_MASTER_KEY_PATH` | Default encryption key path |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_DEFAULT_REGION` | AWS region |
| `AWS_BUCKET_NAME` | Default S3 bucket |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google service account JSON |
| `DROPBOX_ACCESS_TOKEN` | Dropbox API token |

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid usage |

---

## CLI Module Structure

```
src/cli/
├── __init__.py     # Package exports
├── main.py         # Entry point, command registration
├── crypto.py       # encrypt, decrypt
├── cloud.py        # upload, download
├── media.py        # resize, filter, info
├── license.py      # license group
└── medical.py      # medical group
```
