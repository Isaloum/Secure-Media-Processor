#!/usr/bin/env python3
"""Example: Medical imaging pipeline with Secure Media Processor.

This example demonstrates:
1. Reading and processing DICOM files
2. Preprocessing MRI images
3. Running U-Net segmentation
4. Running cancer prediction inference
5. Generating reports

Note: This example requires optional dependencies:
  pip install pydicom nibabel scipy scikit-image torch
"""

import numpy as np
from pathlib import Path


def check_dependencies():
    """Check if medical imaging dependencies are available."""
    deps = {}

    try:
        import pydicom
        deps['pydicom'] = True
    except ImportError:
        deps['pydicom'] = False

    try:
        import torch
        deps['pytorch'] = True
        deps['gpu'] = torch.cuda.is_available()
    except ImportError:
        deps['pytorch'] = False
        deps['gpu'] = False

    try:
        import scipy
        deps['scipy'] = True
    except ImportError:
        deps['scipy'] = False

    print("=== Dependency Check ===")
    print(f"pydicom: {'✓' if deps.get('pydicom') else '✗ (pip install pydicom)'}")
    print(f"PyTorch: {'✓' if deps.get('pytorch') else '✗ (pip install torch)'}")
    print(f"scipy: {'✓' if deps.get('scipy') else '✗ (pip install scipy)'}")
    print(f"GPU: {'✓ Available' if deps.get('gpu') else '✗ CPU only'}")
    print()

    return deps


def example_preprocessing():
    """Demonstrate MRI preprocessing pipeline."""
    print("=== Preprocessing Example ===\n")

    from src.medical.preprocessing import (
        MedicalImagePreprocessor,
        PreprocessingConfig,
        NormalizationMethod
    )

    # Create synthetic MRI-like image
    np.random.seed(42)
    image = np.random.randn(256, 256).astype(np.float32) * 100 + 500
    # Add some structure
    image[100:150, 100:150] += 200  # Simulated lesion

    print(f"Input image shape: {image.shape}")
    print(f"Input range: [{image.min():.1f}, {image.max():.1f}]")
    print(f"Input mean: {image.mean():.1f}, std: {image.std():.1f}\n")

    # Configure preprocessing
    config = PreprocessingConfig(
        normalize=True,
        normalization_method=NormalizationMethod.ZSCORE,
        denoise=True,
        bias_correction=False,  # Skip for synthetic data
        enhance_contrast=False
    )

    # Run preprocessing
    preprocessor = MedicalImagePreprocessor(config)
    result = preprocessor.preprocess(image)

    print("Preprocessing complete!")
    print(f"Output shape: {result.final_shape}")
    print(f"Output range: [{result.data.min():.2f}, {result.data.max():.2f}]")
    print(f"Output mean: {result.data.mean():.2f}, std: {result.data.std():.2f}")
    print(f"\nSteps applied:")
    for step in result.steps_applied:
        print(f"  - {step}")


def example_segmentation():
    """Demonstrate U-Net segmentation."""
    print("\n=== Segmentation Example ===\n")

    from src.medical.unet import (
        UNetSegmentation,
        SegmentationConfig,
        UNetVariant,
        SegmentationMetrics
    )

    # Create synthetic image with "lesion"
    np.random.seed(42)
    image = np.random.randn(256, 256).astype(np.float32) * 0.1

    # Add circular "lesion"
    y, x = np.ogrid[:256, :256]
    center = (128, 128)
    radius = 30
    mask_gt = ((x - center[0])**2 + (y - center[1])**2 <= radius**2).astype(np.float32)
    image += mask_gt * 0.5  # Brighter lesion

    print(f"Input image shape: {image.shape}")
    print(f"Ground truth lesion area: {mask_gt.sum():.0f} pixels\n")

    # Configure segmentation (demo mode - no trained model)
    config = SegmentationConfig(
        variant=UNetVariant.STANDARD,
        use_gpu=False,  # Use CPU for demo
        threshold=0.5
    )

    # Create pipeline
    pipeline = UNetSegmentation(config)
    pipeline.create_model()  # Creates untrained model

    print("Running segmentation (untrained model - demo only)...")
    result = pipeline.segment(image)

    print(f"\nSegmentation Results:")
    print(f"  Regions found: {result.num_regions}")
    print(f"  Total area: {result.total_area} pixels")
    print(f"  Threshold: {result.metadata.get('threshold', 0.5)}")

    # Evaluate against ground truth
    # For demo, create mock prediction matching GT
    mock_prediction = mask_gt  # Perfect prediction for demo

    metrics = SegmentationMetrics.evaluate(
        mock_prediction,
        mask_gt,
        include_surface_metrics=False
    )

    print(f"\nEvaluation Metrics (mock):")
    print(f"  Dice: {metrics['dice']:.4f}")
    print(f"  IoU: {metrics['iou']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall: {metrics['recall']:.4f}")


def example_inference():
    """Demonstrate cancer prediction inference."""
    print("\n=== Inference Example ===\n")

    from src.medical.inference import (
        ModelConfig,
        ModelType,
        PredictionType,
        check_ml_available
    )

    # Check ML backends
    ml_status = check_ml_available()
    print(f"PyTorch available: {ml_status['pytorch']}")
    print(f"GPU available: {ml_status['gpu']}\n")

    if not ml_status['pytorch']:
        print("PyTorch not available. Skipping inference example.")
        return

    # Create synthetic MRI slice
    np.random.seed(42)
    image = np.random.randn(224, 224).astype(np.float32)

    print(f"Input image shape: {image.shape}")

    # Configure model (demo - no actual model file)
    config = ModelConfig(
        model_path="demo_model.pt",  # Would need real model
        model_type=ModelType.PYTORCH,
        prediction_type=PredictionType.BINARY,
        use_gpu=False,
        class_names=["No Cancer", "Cancer"]
    )

    print(f"\nModel Configuration:")
    print(f"  Type: {config.model_type.value}")
    print(f"  Prediction: {config.prediction_type.value}")
    print(f"  Classes: {config.class_names}")
    print(f"  Threshold: {config.threshold}")

    # Note: Real usage would be:
    # pipeline = CancerPredictionPipeline(config)
    # result = pipeline.predict_single(image)

    print("\nNote: Full inference requires a trained model file.")
    print("See docs/api/medical.md for training and usage details.")


def example_full_pipeline():
    """Demonstrate complete medical imaging pipeline."""
    print("\n=== Full Pipeline Example ===\n")

    print("A complete medical imaging pipeline would:")
    print("1. Load DICOM file or series")
    print("2. Extract metadata and pixel data")
    print("3. Preprocess (bias correction, normalization)")
    print("4. Run segmentation to find lesions")
    print("5. Run classification for cancer prediction")
    print("6. Generate clinical report")
    print()

    print("Example CLI usage:")
    print()
    print("  # View DICOM info")
    print("  smp medical dicom-info patient_scan.dcm")
    print()
    print("  # Preprocess for ML")
    print("  smp medical preprocess scan.dcm preprocessed.npy --normalize zscore")
    print()
    print("  # Run segmentation")
    print("  smp medical segment scan.dcm mask.png --model unet.pt --variant attention")
    print()
    print("  # Run prediction")
    print("  smp medical predict scan.dcm --model cancer_model.pt --output-report report.txt")
    print()
    print("  # Evaluate segmentation")
    print("  smp medical evaluate prediction.png ground_truth.png --surface-metrics")


def main():
    """Run medical imaging examples."""
    deps = check_dependencies()

    # Always show preprocessing (works with just numpy)
    try:
        example_preprocessing()
    except Exception as e:
        print(f"Preprocessing example failed: {e}")

    # Segmentation requires PyTorch
    if deps.get('pytorch'):
        try:
            example_segmentation()
        except Exception as e:
            print(f"Segmentation example failed: {e}")
    else:
        print("\n=== Segmentation Example ===")
        print("Skipped: PyTorch not installed")

    # Inference requires PyTorch
    if deps.get('pytorch'):
        try:
            example_inference()
        except Exception as e:
            print(f"Inference example failed: {e}")
    else:
        print("\n=== Inference Example ===")
        print("Skipped: PyTorch not installed")

    # Show full pipeline overview
    example_full_pipeline()


if __name__ == "__main__":
    main()
