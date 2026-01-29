# Medical Researcher's Guide to Secure Media Processor

A step-by-step guide for medical researchers who need to securely process
sensitive medical imaging data (MRI, CT, X-rays) for cancer prediction,
diagnosis assistance, and research.

---

## Why Use This?

**The Problem:** You have MRI scans stored in hospital cloud systems. You need to:
- Download them to your GPU workstation for ML processing
- Keep patient data private (HIPAA compliance)
- Run your cancer prediction models locally
- Ensure audit trails for IRB/ethics review

**The Solution:** Secure Media Processor handles the security plumbing so you can focus on your research.

```
[Hospital Cloud] ──encrypted──► [Your GPU Workstation] ──► [Cancer Prediction]
                                         │
                              Data never leaves unencrypted
                              Full audit trail for compliance
```

---

## Quick Start (5 Minutes)

### 1. Install

```bash
pip install secure-media-processor[medical]
```

This installs:
- Core secure transfer pipeline
- DICOM processing
- MRI preprocessing
- U-Net segmentation models
- Cancer prediction inference

### 2. Configure Cloud Access

Create `~/.smp/config.json`:

```json
{
  "cloud": {
    "provider": "s3",
    "bucket": "hospital-encrypted-data",
    "region": "us-east-1"
  },
  "user_id": "researcher@university.edu",
  "workspace": "~/secure-medical-workspace"
}
```

### 3. Run Your First Analysis

```python
from src.medical import MedicalPipeline

# Initialize pipeline
pipeline = MedicalPipeline(
    cloud_config={
        'provider': 's3',
        'bucket': 'hospital-encrypted-data',
        'region': 'us-east-1'
    },
    user_id='researcher@university.edu'
)

# Process a study (downloads, processes, predicts)
results = pipeline.process_study(
    remote_path='breast-mri/patient-001/',
    operations=['load', 'preprocess', 'segment', 'predict']
)

# View results
print(f"Cancer Probability: {results.cancer_probability:.2%}")
print(f"Prediction: {results.cancer_prediction}")
print(f"Confidence: {results.confidence_score:.2%}")

# IMPORTANT: Secure cleanup when done
pipeline.cleanup()
```

---

## Complete Workflow

### Step 1: Set Up Key Exchange (First Time Only)

For maximum security, set up key exchange with your data source (hospital):

```python
from src.core import KeyExchangeManager, KeyType

# Initialize key manager
km = KeyExchangeManager(key_store_path="~/.smp/keys")

# Generate your key pair
key_id = km.generate_key_pair(
    key_type=KeyType.ECDH_P384,
    purpose="hospital-data-transfer"
)

# Export public key to share with hospital IT
public_key = km.export_public_key(key_id)
print("Send this to hospital IT:")
print(public_key.decode())

# Save to file for easy sharing
with open("my_public_key.pem", "wb") as f:
    f.write(public_key)
```

Give `my_public_key.pem` to the hospital IT team. They will:
1. Encrypt data using your public key before uploading to cloud
2. Give you their public key

This ensures **zero-knowledge transfer** - the cloud provider never sees unencrypted data.

### Step 2: Initialize Pipeline

```python
from src.medical import MedicalPipeline

pipeline = MedicalPipeline(
    # Cloud configuration
    cloud_config={
        'provider': 's3',  # or 'google_drive', 'dropbox'
        'bucket': 'hospital-encrypted-scans',
        'region': 'us-east-1'
    },

    # Security settings
    encryption_key_path='~/.smp/keys/master.key',
    audit_log_path='~/.smp/audit/',
    user_id='dr.smith@cancer-research.org',

    # Processing settings
    workspace='~/secure-workspace/',
    model_path='~/models/breast-cancer-v2.pt',  # Your trained model
    device='cuda',  # GPU acceleration

    # Privacy settings
    auto_anonymize=True,  # Remove patient identifiers
    auto_cleanup=False    # Manual cleanup for verification
)
```

### Step 3: Process Studies

```python
# Process a single study
results = pipeline.process_study(
    remote_path='studies/BREAST-MRI-2024-001/',
    study_id='RESEARCH-001',
    operations=['load', 'anonymize', 'preprocess', 'segment', 'predict'],
    download_mode='zero_knowledge',  # Maximum security
    output_path='./results/RESEARCH-001/'
)

# Access results
print(f"Study: {results.study_id}")
print(f"Cancer Probability: {results.cancer_probability:.4f}")
print(f"Prediction: {results.cancer_prediction}")
print(f"Processing Time: {results.processing_time_seconds:.2f}s")
print(f"Operations: {', '.join(results.operations_performed)}")
```

### Step 4: Batch Processing

```python
# Process multiple studies
study_paths = [
    'studies/BREAST-MRI-2024-001/',
    'studies/BREAST-MRI-2024-002/',
    'studies/BREAST-MRI-2024-003/',
]

all_results = []
for path in study_paths:
    result = pipeline.process_study(
        remote_path=path,
        operations=['preprocess', 'segment', 'predict']
    )
    all_results.append(result)
    print(f"Processed {result.study_id}: {result.cancer_probability:.2%}")

# Summary statistics
probabilities = [r.cancer_probability for r in all_results if r.cancer_probability]
print(f"\nProcessed {len(all_results)} studies")
print(f"Average cancer probability: {sum(probabilities)/len(probabilities):.2%}")
```

### Step 5: Compliance Reporting

```python
# Export audit log for IRB review
entries = pipeline.export_audit_log(
    output_path='./compliance/audit_report_2024.json',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
print(f"Exported {entries} audit entries")

# Verify audit log integrity (detect tampering)
summary = pipeline.get_audit_summary()
print(f"Integrity verified: {summary['integrity_verified']}")
```

### Step 6: Secure Cleanup

```python
# CRITICAL: Always cleanup sensitive data
pipeline.cleanup()
print("All sensitive data securely deleted")
```

---

## Understanding the Operations

| Operation | What It Does | When to Use |
|-----------|--------------|-------------|
| `load` | Reads DICOM files, extracts metadata | Always (required) |
| `anonymize` | Removes patient identifiers | Research studies (recommended) |
| `preprocess` | Normalizes, denoises, corrects bias | Before ML inference |
| `segment` | U-Net segmentation of regions | Tumor detection |
| `predict` | Cancer probability prediction | Diagnostic assistance |

### Minimal Pipeline (Fast)

```python
# Just load and predict (skip preprocessing)
results = pipeline.process_study(
    remote_path='...',
    operations=['load', 'predict']
)
```

### Full Pipeline (Best Quality)

```python
# All operations for best results
results = pipeline.process_study(
    remote_path='...',
    operations=['load', 'anonymize', 'preprocess', 'segment', 'predict']
)
```

---

## Using Your Own Models

### PyTorch Model

```python
pipeline = MedicalPipeline(
    model_path='~/models/my_breast_cancer_model.pt',
    device='cuda'
)
```

### ONNX Model (Faster Inference)

```python
pipeline = MedicalPipeline(
    model_path='~/models/my_model.onnx',
    device='cuda'  # Uses ONNX Runtime with CUDA
)
```

### Custom Model Integration

If your model has a custom interface:

```python
from src.medical import MedicalPipeline, MedicalStudyResult

class MyCustomPipeline(MedicalPipeline):
    def _predict(self, volume, mask):
        # Load your custom model
        import torch
        model = torch.load(self._model_path)
        model.eval()

        # Your custom preprocessing
        input_tensor = self._prepare_input(volume, mask)

        # Inference
        with torch.no_grad():
            output = model(input_tensor)

        probability = torch.sigmoid(output).item()

        return {
            'probability': probability,
            'prediction': 'positive' if probability > 0.5 else 'negative',
            'confidence': abs(probability - 0.5) * 2
        }
```

---

## HIPAA Compliance Checklist

Secure Media Processor helps you meet HIPAA requirements:

| Requirement | How SMP Addresses It |
|-------------|---------------------|
| **Access Controls** | Data decrypted only on local workstation |
| **Audit Controls** | Complete audit trail with hash chain verification |
| **Transmission Security** | AES-256-GCM encryption + TLS |
| **Integrity Controls** | SHA-256 checksums on all transfers |
| **Data Disposal** | DoD 5220.22-M secure deletion |

### For IRB Submissions

Include in your IRB protocol:

> "Medical imaging data will be transferred using Secure Media Processor,
> which provides AES-256-GCM encryption, HIPAA-compliant audit logging,
> and secure deletion after processing. All data processing occurs on
> local GPU workstations; cloud providers never have access to
> unencrypted patient data."

---

## Troubleshooting

### "No DICOM files found"

Check file extensions:
```python
# SMP looks for .dcm and .DCM files
# If your files have no extension, rename them:
import os
for f in os.listdir('dicom_folder'):
    os.rename(f, f + '.dcm')
```

### "CUDA out of memory"

Reduce batch size or use CPU:
```python
pipeline = MedicalPipeline(
    device='cpu'  # Use CPU instead of GPU
)
```

### "Connection refused" (Cloud)

Check your AWS/GCS/Dropbox credentials:
```bash
# For AWS S3
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Or use ~/.aws/credentials
```

### "Integrity verification failed"

Data may have been corrupted in transfer. Re-download:
```python
# Force re-download
pipeline.process_study(
    remote_path='...',
    operations=['load'],  # Just re-download
    download_mode='standard'  # Try standard mode
)
```

---

## Example: Breast Cancer Research Study

Complete example for a breast cancer screening research study:

```python
#!/usr/bin/env python3
"""
Breast Cancer Screening Research Study
Using Secure Media Processor

IRB Protocol: IRB-2024-0042
Principal Investigator: Dr. Jane Smith
"""

from src.medical import MedicalPipeline
import json
from datetime import datetime

# Configuration
CONFIG = {
    'cloud': {
        'provider': 's3',
        'bucket': 'hospital-breast-mri-encrypted',
        'region': 'us-east-1'
    },
    'user_id': 'dr.smith@university.edu',
    'study_protocol': 'BREAST-SCREEN-2024'
}

def main():
    # Initialize pipeline
    pipeline = MedicalPipeline(
        cloud_config=CONFIG['cloud'],
        user_id=CONFIG['user_id'],
        auto_anonymize=True,  # Required for research
        device='cuda'
    )

    # Studies to process (from enrollment database)
    study_ids = [
        'BREAST-MRI-001',
        'BREAST-MRI-002',
        'BREAST-MRI-003',
        # ... etc
    ]

    # Process all studies
    results_summary = []

    for study_id in study_ids:
        print(f"\nProcessing {study_id}...")

        try:
            result = pipeline.process_study(
                remote_path=f'studies/{study_id}/',
                study_id=study_id,
                operations=['load', 'anonymize', 'preprocess', 'segment', 'predict'],
                output_path=f'./results/{study_id}/'
            )

            results_summary.append({
                'study_id': study_id,
                'probability': result.cancer_probability,
                'prediction': result.cancer_prediction,
                'confidence': result.confidence_score,
                'processed_at': result.processed_at.isoformat()
            })

            print(f"  Result: {result.cancer_prediction} "
                  f"(probability: {result.cancer_probability:.2%})")

        except Exception as e:
            print(f"  ERROR: {e}")
            results_summary.append({
                'study_id': study_id,
                'error': str(e)
            })

    # Save summary
    with open('./results/study_summary.json', 'w') as f:
        json.dump({
            'protocol': CONFIG['study_protocol'],
            'processed_at': datetime.utcnow().isoformat(),
            'total_studies': len(study_ids),
            'results': results_summary
        }, f, indent=2)

    # Export audit log for IRB
    pipeline.export_audit_log('./compliance/audit_log.json')

    # Cleanup all sensitive data
    pipeline.cleanup()
    print("\nAll sensitive data securely deleted")

    # Print summary
    successful = [r for r in results_summary if 'probability' in r]
    print(f"\n{'='*50}")
    print(f"Study Complete")
    print(f"{'='*50}")
    print(f"Total processed: {len(successful)}/{len(study_ids)}")
    print(f"High risk (>70%): {len([r for r in successful if r['probability'] > 0.7])}")
    print(f"Results saved to: ./results/")
    print(f"Audit log saved to: ./compliance/audit_log.json")

if __name__ == '__main__':
    main()
```

---

## Getting Help

- **Issues:** https://github.com/Isaloum/Secure-Media-Processor/issues
- **Documentation:** https://github.com/Isaloum/Secure-Media-Processor/docs/

---

**Remember:** Always call `pipeline.cleanup()` when done to securely delete sensitive data!
