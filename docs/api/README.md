# API Reference

This directory contains the API reference documentation for Secure Media Processor.

## Modules

| Module | Description |
|--------|-------------|
| [core.md](core.md) | Core modules: encryption, config, rate limiting |
| [cloud.md](cloud.md) | Cloud storage connectors: S3, Google Drive, Dropbox |
| [medical.md](medical.md) | Medical imaging: DICOM, U-Net, ML inference |
| [cli.md](cli.md) | Command-line interface reference |

## Quick Links

### Encryption
```python
from src.encryption import MediaEncryptor

encryptor = MediaEncryptor()
encryptor.encrypt_file("input.jpg", "output.enc")
encryptor.decrypt_file("output.enc", "decrypted.jpg")
```

### Cloud Storage
```python
from src.cloud.connectors import S3Connector

connector = S3Connector(bucket_name="my-bucket")
connector.upload_file("file.enc", "remote/path/file.enc")
```

### Medical Imaging
```python
from src.medical.inference import CancerPredictionPipeline, ModelConfig

config = ModelConfig(model_path="model.pt")
pipeline = CancerPredictionPipeline(config)
result = pipeline.predict_from_dicom("scan.dcm")
```

## Import Patterns

### New-style imports (recommended)
```python
from src.core.encryption import MediaEncryptor
from src.cloud.connectors import S3Connector, ConnectorManager
from src.medical.inference import CancerPredictionPipeline
from src.cli import cli
```

### Legacy imports (backward compatible)
```python
from src.encryption import MediaEncryptor
from src.connectors import S3Connector
from src.ml_inference import CancerPredictionPipeline
```

Both import styles work - legacy imports are shims that re-export from new locations.
