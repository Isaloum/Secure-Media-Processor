# Medical Imaging API Reference

The medical package provides DICOM processing, MRI preprocessing, U-Net segmentation, and ML inference for cancer prediction.

## Location

```
src/medical/
├── __init__.py
├── dicom.py              # DICOM file processing
├── preprocessing.py      # MRI preprocessing pipeline
├── unet/                 # U-Net segmentation
│   ├── __init__.py
│   ├── models.py         # Network architectures
│   ├── losses.py         # Loss functions
│   ├── metrics.py        # Evaluation metrics
│   ├── postprocessing.py # Mask post-processing
│   └── inference.py      # Segmentation pipeline
└── inference/            # ML inference
    ├── __init__.py
    ├── config.py         # Configuration classes
    ├── loaders.py        # Model loaders
    └── pipeline.py       # Prediction pipeline
```

---

## dicom.py - DICOMProcessor

Process DICOM medical imaging files.

```python
from src.medical.dicom import DICOMProcessor
from src.dicom_processor import check_dicom_available
```

### Constructor

```python
DICOMProcessor()
```

### Methods

#### read_dicom()

```python
def read_dicom(
    self,
    path: str
) -> Tuple[np.ndarray, DICOMMetadata]
```

Read single DICOM file.

**Returns:** Tuple of (pixel_array, metadata)

#### read_dicom_series()

```python
def read_dicom_series(
    self,
    directory: str
) -> DICOMVolume
```

Read DICOM series from directory.

#### anonymize_dicom()

```python
def anonymize_dicom(
    self,
    input_path: str,
    output_path: str,
    keep_study_uid: bool = False
) -> Dict[str, Any]
```

Anonymize DICOM file for HIPAA compliance.

#### convert_to_png()

```python
def convert_to_png(
    self,
    input_path: str,
    output_path: str,
    window_center: Optional[float] = None,
    window_width: Optional[float] = None
) -> Dict[str, Any]
```

#### convert_to_nifti()

```python
def convert_to_nifti(
    self,
    input_path: str,
    output_path: str
) -> Dict[str, Any]
```

### Example

```python
from src.medical.dicom import DICOMProcessor

processor = DICOMProcessor()

# Read single file
pixels, metadata = processor.read_dicom("scan.dcm")
print(f"Image size: {metadata.rows} x {metadata.columns}")
print(f"Modality: {metadata.modality}")

# Read series
volume = processor.read_dicom_series("./scans/")
print(f"Volume shape: {volume.pixel_data.shape}")

# Anonymize for sharing
result = processor.anonymize_dicom("scan.dcm", "anon_scan.dcm")
print(f"Removed fields: {result['removed_fields']}")

# Convert to PNG for visualization
processor.convert_to_png("scan.dcm", "scan.png")
```

---

## preprocessing.py - MedicalImagePreprocessor

Preprocess medical images for ML analysis.

```python
from src.medical.preprocessing import (
    MedicalImagePreprocessor,
    PreprocessingConfig,
    NormalizationMethod
)
```

### NormalizationMethod (Enum)

```python
class NormalizationMethod(Enum):
    ZSCORE = "zscore"       # Zero mean, unit variance
    MINMAX = "minmax"       # Scale to [0, 1]
    PERCENTILE = "percentile"  # Clip outliers, then scale
```

### PreprocessingConfig

```python
@dataclass
class PreprocessingConfig:
    normalize: bool = True
    normalization_method: NormalizationMethod = NormalizationMethod.ZSCORE
    denoise: bool = True
    bias_correction: bool = True
    enhance_contrast: bool = False
    target_spacing: Optional[Tuple[float, ...]] = None
```

### MedicalImagePreprocessor

```python
class MedicalImagePreprocessor:
    def __init__(self, config: PreprocessingConfig)
    def preprocess(self, image: np.ndarray) -> PreprocessingResult
```

### Example

```python
from src.medical.preprocessing import (
    MedicalImagePreprocessor,
    PreprocessingConfig,
    NormalizationMethod
)

config = PreprocessingConfig(
    normalize=True,
    normalization_method=NormalizationMethod.ZSCORE,
    denoise=True,
    bias_correction=True
)

preprocessor = MedicalImagePreprocessor(config)
result = preprocessor.preprocess(mri_image)

print(f"Original shape: {result.original_shape}")
print(f"Steps applied: {result.steps_applied}")
```

---

## unet/ - U-Net Segmentation

Deep learning segmentation for tumor/lesion detection.

```python
from src.medical.unet import (
    UNetSegmentation,
    SegmentationConfig,
    UNetVariant,
    SegmentationMetrics
)
```

### UNetVariant (Enum)

```python
class UNetVariant(Enum):
    STANDARD = "standard"    # Classic U-Net
    ATTENTION = "attention"  # With attention gates
    RESIDUAL = "residual"    # With residual connections
```

### SegmentationConfig

```python
@dataclass
class SegmentationConfig:
    variant: UNetVariant = UNetVariant.STANDARD
    in_channels: int = 1
    out_channels: int = 1
    use_gpu: bool = True
    threshold: float = 0.5
    apply_post_processing: bool = True
```

### UNetSegmentation

```python
class UNetSegmentation:
    def __init__(self, config: SegmentationConfig)
    def create_model(self) -> None
    def load_model(self, path: str) -> None
    def segment(self, image: np.ndarray) -> SegmentationResult
    def segment_from_dicom(self, path: str) -> Dict[str, Any]
```

### SegmentationMetrics

```python
class SegmentationMetrics:
    @staticmethod
    def evaluate(
        prediction: np.ndarray,
        ground_truth: np.ndarray,
        include_surface_metrics: bool = False
    ) -> Dict[str, float]
```

Returns: `dice`, `iou`, `precision`, `recall`, `specificity`, and optionally `hausdorff_distance`, `average_surface_distance`.

### Example

```python
from src.medical.unet import (
    UNetSegmentation,
    SegmentationConfig,
    UNetVariant,
    SegmentationMetrics
)

# Configure
config = SegmentationConfig(
    variant=UNetVariant.ATTENTION,
    use_gpu=True,
    threshold=0.5
)

# Create pipeline
pipeline = UNetSegmentation(config)
pipeline.load_model("tumor_model.pt")

# Segment
result = pipeline.segment(mri_slice)
print(f"Regions found: {result.num_regions}")
print(f"Total area: {result.total_area} pixels")

# Evaluate against ground truth
metrics = SegmentationMetrics.evaluate(result.mask, ground_truth)
print(f"Dice: {metrics['dice']:.4f}")
print(f"IoU: {metrics['iou']:.4f}")
```

---

## inference/ - ML Inference Pipeline

End-to-end cancer prediction from MRI.

```python
from src.medical.inference import (
    CancerPredictionPipeline,
    ModelConfig,
    ModelType,
    PredictionType,
    check_ml_available
)
```

### ModelType (Enum)

```python
class ModelType(Enum):
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TORCHSCRIPT = "torchscript"
```

### PredictionType (Enum)

```python
class PredictionType(Enum):
    BINARY = "binary"          # Cancer / No Cancer
    MULTICLASS = "multiclass"  # Multiple stages
    REGRESSION = "regression"  # Risk score
    SEGMENTATION = "segmentation"
```

### ModelConfig

```python
@dataclass
class ModelConfig:
    model_path: str
    model_type: ModelType = ModelType.PYTORCH
    prediction_type: PredictionType = PredictionType.BINARY
    input_shape: Tuple[int, ...] = (1, 1, 224, 224)
    num_classes: int = 2
    class_names: List[str] = ["No Cancer", "Cancer"]
    threshold: float = 0.5
    use_gpu: bool = True
    batch_size: int = 1
```

### CancerPredictionPipeline

```python
class CancerPredictionPipeline:
    def __init__(self, config: ModelConfig, use_preprocessing: bool = True)
    def predict_single(self, image: np.ndarray) -> Dict[str, Any]
    def predict_volume(self, volume: np.ndarray) -> Dict[str, Any]
    def predict_from_dicom(self, path: str) -> Dict[str, Any]
```

### Example

```python
from src.medical.inference import (
    CancerPredictionPipeline,
    ModelConfig,
    ModelType,
    PredictionType
)

# Configure model
config = ModelConfig(
    model_path="breast_cancer_model.pt",
    model_type=ModelType.PYTORCH,
    prediction_type=PredictionType.BINARY,
    use_gpu=True,
    class_names=["No Cancer", "Cancer"]
)

# Create pipeline
pipeline = CancerPredictionPipeline(config, use_preprocessing=True)

# Predict from DICOM
result = pipeline.predict_from_dicom("patient_scan/")

print(f"Prediction: {result['predicted_label']}")
print(f"Confidence: {result['confidence']*100:.1f}%")
print(f"Most suspicious slice: #{result['most_suspicious_slice']}")

# Print report
print(result['report'])
```

---

## Checking Dependencies

```python
from src.dicom_processor import check_dicom_available
from src.medical.inference import check_ml_available
from src.unet_segmentation import check_segmentation_available

# Check DICOM support
if check_dicom_available():
    print("DICOM: ✓")

# Check ML backends
ml = check_ml_available()
print(f"PyTorch: {'✓' if ml['pytorch'] else '✗'}")
print(f"ONNX: {'✓' if ml['onnx'] else '✗'}")
print(f"GPU: {'✓' if ml['gpu'] else '✗'}")

# Check segmentation
seg = check_segmentation_available()
print(f"U-Net ready: {seg['pytorch'] and seg['scipy']}")
```

---

## Install Dependencies

```bash
# Core medical imaging
pip install pydicom nibabel

# ML inference
pip install torch torchvision

# Preprocessing & segmentation
pip install scipy scikit-image

# ONNX support (optional)
pip install onnxruntime

# All at once
pip install pydicom nibabel scipy scikit-image torch torchvision
```
