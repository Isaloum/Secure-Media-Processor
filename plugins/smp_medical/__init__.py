"""
SMP Medical Imaging Plugin

This plugin extends Secure Media Processor with medical imaging capabilities:
- DICOM file processing
- U-Net segmentation models
- Medical image preprocessing
- Cancer prediction inference

This is a SEPARATE plugin - install it only if you need medical imaging features.

Installation:
    pip install smp-medical

    # Or from the main package with extras:
    pip install secure-media-processor[medical]

Usage:
    from secure_media_processor import Pipeline
    from smp_medical import MedicalImagingPlugin

    pipeline = Pipeline()
    pipeline.register_plugin(MedicalImagingPlugin())

    # Download encrypted DICOM files
    pipeline.secure_download("s3://hospital/scans/")

    # Process locally with medical imaging
    results = pipeline.process_local()

Note: This plugin is maintained separately from the core SMP package.
The core package focuses on secure data transfer; this plugin adds
domain-specific processing capabilities for medical imaging.
"""

from plugins import ProcessorPlugin, PluginMetadata

# Version of the medical imaging plugin
__version__ = "1.0.0"

# Supported medical image formats
SUPPORTED_FORMATS = [
    'dcm',      # DICOM
    'dicom',
    'nii',      # NIfTI
    'nii.gz',
    'mha',      # MetaImage
    'mhd',
    'nrrd',     # Nearly Raw Raster Data
]


class MedicalImagingPlugin(ProcessorPlugin):
    """
    Medical Imaging processor plugin for Secure Media Processor.

    This plugin provides:
    - DICOM file loading and metadata extraction
    - Medical image preprocessing (windowing, normalization)
    - U-Net segmentation for medical images
    - Integration with cancer prediction models

    The plugin processes data LOCALLY on the GPU workstation.
    No medical data is sent to external services.
    """

    def __init__(self, model_path: str = None, device: str = "auto"):
        """
        Initialize the medical imaging plugin.

        Args:
            model_path: Path to pre-trained model weights
            device: Device to use ('cpu', 'cuda', 'auto')
        """
        self._model_path = model_path
        self._device = device
        self._model = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="medical-imaging",
            version=__version__,
            description="Medical imaging processing with DICOM support and U-Net segmentation",
            author="Secure Media Processor Contributors",
            requires_gpu=True,
            supported_formats=SUPPORTED_FORMATS
        )

    def setup(self) -> None:
        """Initialize medical imaging resources."""
        # Lazy import to avoid loading heavy dependencies unless needed
        try:
            from src.medical import dicom, preprocessing
            from src.medical.unet import inference
            self._dicom = dicom
            self._preprocessing = preprocessing
            self._inference = inference
        except ImportError as e:
            raise ImportError(
                "Medical imaging dependencies not installed. "
                "Install with: pip install secure-media-processor[medical]"
            ) from e

    def teardown(self) -> None:
        """Clean up resources."""
        self._model = None

    def validate_input(self, data) -> bool:
        """Check if input is a supported medical image format."""
        if isinstance(data, str):
            # Check file extension
            lower_data = data.lower()
            return any(lower_data.endswith(f'.{fmt}') for fmt in SUPPORTED_FORMATS)
        return False

    def process(self, data, **kwargs):
        """
        Process medical imaging data.

        Args:
            data: Path to medical image file or directory
            **kwargs: Processing options
                - operation: 'load', 'preprocess', 'segment', 'predict'
                - model_name: Model to use for segmentation/prediction
                - output_path: Where to save results

        Returns:
            Processed results (varies by operation)
        """
        operation = kwargs.get('operation', 'load')

        if operation == 'load':
            return self._load_medical_image(data, **kwargs)
        elif operation == 'preprocess':
            return self._preprocess(data, **kwargs)
        elif operation == 'segment':
            return self._segment(data, **kwargs)
        elif operation == 'predict':
            return self._predict(data, **kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _load_medical_image(self, path: str, **kwargs):
        """Load a medical image file."""
        return self._dicom.load_dicom(path)

    def _preprocess(self, data, **kwargs):
        """Preprocess medical image data."""
        return self._preprocessing.preprocess(data, **kwargs)

    def _segment(self, data, **kwargs):
        """Run U-Net segmentation."""
        return self._inference.segment(data, **kwargs)

    def _predict(self, data, **kwargs):
        """Run cancer prediction inference."""
        return self._inference.predict(data, **kwargs)


# Convenience function for quick setup
def create_plugin(**kwargs) -> MedicalImagingPlugin:
    """Create and return a configured MedicalImagingPlugin."""
    return MedicalImagingPlugin(**kwargs)
