# Secure Media Processor - Refocus Roadmap

## Executive Summary

This document outlines the strategic refocusing of Secure Media Processor from a mixed-purpose media/medical imaging tool to its **core mission**: providing a **secure data pipeline for transferring sensitive data from cloud/premises to local GPU processing**.

---

## The Original Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   [Hospital/Cloud/Premises]  ══════════►  [Local GPU Workstation]          │
│                                    │                                        │
│                              ┌─────┴─────┐                                  │
│                              │ ENCRYPTED │                                  │
│                              │  SECURE   │                                  │
│                              │ PIPELINE  │                                  │
│                              └───────────┘                                  │
│                                                                             │
│   "A safe, secure way to download and process sensitive data on GPU        │
│    instead of leaving it vulnerable in the cloud"                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Use Case**: Medical researchers (like the astrophysicist working on breast cancer MRI prediction) need to:
1. Download sensitive medical images from cloud/hospital systems
2. Process them securely on local GPU
3. Never expose unencrypted data outside the local machine
4. Maintain audit trails for compliance (HIPAA, GDPR)

---

## Problem: Scope Creep

The project evolved to include:

| Component | Lines of Code | Core Mission? |
|-----------|---------------|---------------|
| `encryption.py` | 400+ | ✅ YES - Core |
| `cloud_storage.py` | 300+ | ✅ YES - Core |
| `connectors/*` | 1,200+ | ✅ YES - Core |
| `gpu_processor.py` | 500+ | ⚠️ PARTIAL - Basic processing only |
| `unet_segmentation.py` | 1,157 | ❌ NO - Medical domain |
| `ml_inference.py` | 779 | ❌ NO - Medical domain |
| `dicom_processor.py` | 600+ | ❌ NO - Medical domain |
| `medical_preprocessing.py` | 400+ | ❌ NO - Medical domain |

**~40% of the codebase is medical imaging processing** - this is the researcher's job, not the pipeline's job.

---

## Solution: Three-Phase Refocus

### Phase 1: REFOCUS - Define True Product Scope

**Core Product: Secure GPU Data Pipeline**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SECURE-MEDIA-PROCESSOR (Core)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   INGEST     │    │   SECURE     │    │   DELIVER    │                  │
│  │              │───►│   TRANSIT    │───►│              │                  │
│  │ • Cloud APIs │    │              │    │ • GPU Memory │                  │
│  │ • Local FS   │    │ • AES-256    │    │ • Local FS   │                  │
│  │ • SFTP/SCP   │    │ • Zero-Know  │    │ • Encrypted  │                  │
│  │ • Hospital   │    │ • Audit Log  │    │   at Rest    │                  │
│  │   Systems    │    │ • Integrity  │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                             │
│  Features:                                                                  │
│  ✅ End-to-end encryption (AES-256-GCM)                                    │
│  ✅ Multi-cloud connectors (S3, GDrive, Dropbox)                           │
│  🔲 Secure key exchange (Diffie-Hellman / RSA)                             │
│  🔲 Zero-knowledge transfer mode                                           │
│  🔲 HIPAA/GDPR audit logging                                               │
│  🔲 Data-at-rest encryption on GPU workstation                             │
│  🔲 Secure deletion (multi-pass overwrite)                                 │
│  🔲 Memory encryption during processing                                    │
│  🔲 Integrity verification (SHA-256 + signatures)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**What Gets Removed from Core:**
- U-Net segmentation models
- Cancer prediction ML inference
- DICOM-specific processing
- Medical image preprocessing

**What Stays:**
- Encryption/decryption
- Cloud connectors
- Basic GPU-accelerated image operations (resize, transform)
- CLI for pipeline operations
- Audit logging

---

### Phase 2: SPLIT - Separate Medical Imaging Plugin

**New Repository Structure:**

```
BEFORE (monolith):
secure-media-processor/
├── src/
│   ├── encryption.py           # Core
│   ├── connectors/             # Core
│   ├── gpu_processor.py        # Core (basic)
│   ├── unet_segmentation.py    # Medical ❌
│   ├── ml_inference.py         # Medical ❌
│   ├── dicom_processor.py      # Medical ❌
│   └── medical_preprocessing.py # Medical ❌

AFTER (separated):
secure-media-processor/           # Core package (PyPI: secure-media-processor)
├── src/
│   ├── encryption.py
│   ├── connectors/
│   ├── gpu_processor.py
│   ├── secure_transfer.py      # NEW: Core transfer logic
│   ├── audit_logger.py         # NEW: Compliance logging
│   ├── key_exchange.py         # NEW: Secure key management
│   └── cli.py                  # Simplified CLI
├── plugins/                    # Plugin architecture
│   └── __init__.py

secure-media-processor-medical/   # Separate package (PyPI: smp-medical)
├── smp_medical/
│   ├── unet_segmentation.py
│   ├── ml_inference.py
│   ├── dicom_processor.py
│   ├── medical_preprocessing.py
│   └── cancer_prediction.py
└── setup.py
```

**Plugin Architecture:**

```python
# Core package provides hooks for plugins
from secure_media_processor import Pipeline
from smp_medical import CancerPredictionProcessor  # Optional plugin

pipeline = Pipeline()
pipeline.register_processor(CancerPredictionProcessor())  # Extensible

# Download encrypted medical images
pipeline.secure_download("s3://hospital-data/mri-scans/")

# Process with registered plugins (runs on local GPU)
results = pipeline.process_local()

# Results never leave local machine
pipeline.save_results("./local_results/", encrypted=True)
```

---

### Phase 3: DOCUMENT - Architecture & API Reference

**Documentation Structure:**

```
docs/
├── architecture/
│   ├── SECURITY_MODEL.md       # Threat model, encryption details
│   ├── DATA_FLOW.md            # How data moves through the system
│   ├── COMPLIANCE.md           # HIPAA, GDPR considerations
│   └── GPU_PROCESSING.md       # Local GPU security model
├── api/
│   ├── ENCRYPTION_API.md       # Encryption module reference
│   ├── CONNECTORS_API.md       # Cloud connector reference
│   ├── PIPELINE_API.md         # Core pipeline reference
│   └── PLUGIN_API.md           # How to build plugins
├── guides/
│   ├── QUICK_START.md          # 5-minute getting started
│   ├── MEDICAL_IMAGING.md      # Using medical imaging plugin
│   ├── HOSPITAL_INTEGRATION.md # Connecting to hospital systems
│   └── COMPLIANCE_GUIDE.md     # Meeting regulatory requirements
└── examples/
    ├── basic_transfer.py       # Simple encrypted transfer
    ├── multi_cloud_sync.py     # Cross-cloud operations
    ├── medical_pipeline.py     # Medical imaging workflow
    └── audit_logging.py        # Compliance logging example
```

---

## Implementation Timeline

### Week 1: REFOCUS
- [ ] Audit all modules and classify as Core vs Medical
- [ ] Define core module interfaces
- [ ] Create migration plan for medical code

### Week 2: SPLIT
- [ ] Create plugin architecture in core package
- [ ] Move medical imaging code to separate directory
- [ ] Update imports and dependencies
- [ ] Create separate package configuration for medical plugin

### Week 3: DOCUMENT
- [ ] Write security architecture document
- [ ] Create API reference for all core modules
- [ ] Write integration guide
- [ ] Update README with new vision

### Week 4: RELEASE
- [ ] Version 2.0.0 release (refocused core)
- [ ] Version 1.0.0 of smp-medical plugin
- [ ] Update PyPI packages
- [ ] Announce refocus to users

---

## New Feature Roadmap (Post-Refocus)

### Security Features (Priority)
| Feature | Description | Status |
|---------|-------------|--------|
| Secure Key Exchange | RSA/ECDH key exchange for multi-party transfers | 🔲 Planned |
| Zero-Knowledge Mode | Server never sees unencrypted data | 🔲 Planned |
| HIPAA Audit Logging | Compliant audit trails | 🔲 Planned |
| Memory Encryption | Encrypt data in GPU memory | 🔲 Research |
| Secure Deletion | DoD 5220.22-M compliant deletion | 🔲 Planned |
| Hardware Security Module | HSM integration for keys | 🔲 Future |

### Connectivity Features
| Feature | Description | Status |
|---------|-------------|--------|
| Azure Blob Storage | Azure connector | 🔲 Planned |
| SFTP/SCP Connector | Legacy system integration | 🔲 Planned |
| DICOM Network | Hospital PACS integration | 🔲 Planned |
| HL7 FHIR Support | Healthcare data exchange | 🔲 Future |

### Infrastructure Features
| Feature | Description | Status |
|---------|-------------|--------|
| Docker Support | Containerized deployment | 🔲 Planned |
| Kubernetes Operator | K8s native deployment | 🔲 Future |
| REST API Server | Programmatic access | 🔲 Planned |
| Web Dashboard | Monitoring UI | 🔲 Future |

---

## Success Metrics

After refocus, the project should:

1. **Clear Value Proposition**: "Secure pipeline for sensitive data to GPU"
2. **Smaller Core**: < 3,000 lines of core code (down from 6,000+)
3. **Plugin Ecosystem**: Medical imaging as first plugin
4. **Security First**: All new features prioritize security
5. **Compliance Ready**: HIPAA/GDPR audit capabilities built-in

---

## Who Does What

| Role | Responsibility |
|------|----------------|
| **You (Secure Media Processor)** | Secure pipeline, encryption, cloud connectors, audit logging |
| **Your Friend (Astrophysicist)** | Cancer prediction models, medical image analysis, U-Net training |
| **Plugin Architecture** | Connects the two cleanly |

Your friend can focus on the **science** (cancer detection algorithms).
You focus on the **infrastructure** (getting data to them securely).

---

## Next Steps

1. **Approve this roadmap**
2. **Begin Phase 1: REFOCUS** - Audit and classify modules
3. **Create issues/tasks** for each work item
4. **Start implementation**

Ready to proceed?
