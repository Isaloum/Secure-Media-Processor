"""Tests for U-Net segmentation module."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from src.unet_segmentation import (
    UNetVariant,
    SegmentationConfig,
    SegmentationResult,
    SegmentationMetrics,
    SegmentationPostProcessor,
    check_segmentation_available,
    TORCH_AVAILABLE,
    SCIPY_AVAILABLE,
    SKIMAGE_AVAILABLE,
)


class TestUNetVariant:
    """Tests for UNetVariant enum."""

    def test_variant_values(self):
        """Test enum values."""
        assert UNetVariant.STANDARD.value == "standard"
        assert UNetVariant.ATTENTION.value == "attention"
        assert UNetVariant.RESIDUAL.value == "residual"

    def test_variant_from_string(self):
        """Test enum lookup by value."""
        assert UNetVariant("standard") == UNetVariant.STANDARD
        assert UNetVariant("attention") == UNetVariant.ATTENTION
        assert UNetVariant("residual") == UNetVariant.RESIDUAL


class TestSegmentationConfig:
    """Tests for SegmentationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SegmentationConfig()

        assert config.variant == UNetVariant.STANDARD
        assert config.in_channels == 1
        assert config.out_channels == 1
        assert config.base_features == 64
        assert config.depth == 4
        assert config.input_size == (256, 256)
        assert config.normalize_input is True
        assert config.use_gpu is True
        assert config.batch_size == 1
        assert config.threshold == 0.5
        assert config.apply_post_processing is True
        assert config.min_object_size == 100
        assert config.fill_holes is True
        assert config.num_classes == 1
        assert config.class_names == ["Tumor"]

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SegmentationConfig(
            variant=UNetVariant.ATTENTION,
            in_channels=3,
            out_channels=2,
            base_features=32,
            input_size=(512, 512),
            threshold=0.7,
            min_object_size=50,
            class_names=["Background", "Lesion"]
        )

        assert config.variant == UNetVariant.ATTENTION
        assert config.in_channels == 3
        assert config.out_channels == 2
        assert config.base_features == 32
        assert config.input_size == (512, 512)
        assert config.threshold == 0.7
        assert config.min_object_size == 50
        assert config.class_names == ["Background", "Lesion"]


class TestSegmentationResult:
    """Tests for SegmentationResult dataclass."""

    def test_result_creation(self):
        """Test creating a segmentation result."""
        mask = np.zeros((64, 64), dtype=np.uint8)
        mask[20:40, 20:40] = 1
        prob_map = np.random.rand(64, 64).astype(np.float32)

        result = SegmentationResult(
            mask=mask,
            probability_map=prob_map,
            original_shape=(64, 64),
            num_regions=1,
            total_area=400,
            regions=[{"label": 1, "area": 400}],
            metadata={"threshold": 0.5}
        )

        assert result.mask.shape == (64, 64)
        assert result.probability_map.shape == (64, 64)
        assert result.original_shape == (64, 64)
        assert result.num_regions == 1
        assert result.total_area == 400
        assert len(result.regions) == 1
        assert result.metadata["threshold"] == 0.5

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        mask = np.zeros((32, 32), dtype=np.uint8)
        prob_map = np.random.rand(32, 32).astype(np.float32)

        result = SegmentationResult(
            mask=mask,
            probability_map=prob_map,
            original_shape=(32, 32),
            num_regions=2,
            total_area=150,
            regions=[{"label": 1, "area": 100}, {"label": 2, "area": 50}],
            metadata={"device": "cpu"}
        )

        result_dict = result.to_dict()

        assert result_dict["num_regions"] == 2
        assert result_dict["total_area"] == 150
        assert len(result_dict["regions"]) == 2
        assert result_dict["mask_shape"] == [32, 32]
        assert result_dict["metadata"]["device"] == "cpu"


class TestSegmentationMetrics:
    """Tests for SegmentationMetrics class."""

    def test_dice_coefficient_perfect(self):
        """Test Dice coefficient with perfect overlap."""
        pred = np.ones((10, 10), dtype=bool)
        target = np.ones((10, 10), dtype=bool)

        dice = SegmentationMetrics.dice_coefficient(pred, target)
        assert dice > 0.99  # Should be ~1.0

    def test_dice_coefficient_no_overlap(self):
        """Test Dice coefficient with no overlap."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[:5, :] = True
        target = np.zeros((10, 10), dtype=bool)
        target[5:, :] = True

        dice = SegmentationMetrics.dice_coefficient(pred, target)
        assert dice < 0.01  # Should be ~0

    def test_dice_coefficient_partial_overlap(self):
        """Test Dice coefficient with partial overlap."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[2:8, 2:8] = True
        target = np.zeros((10, 10), dtype=bool)
        target[4:10, 4:10] = True

        dice = SegmentationMetrics.dice_coefficient(pred, target)
        assert 0.2 < dice < 0.8

    def test_iou_perfect(self):
        """Test IoU with perfect overlap."""
        pred = np.ones((10, 10), dtype=bool)
        target = np.ones((10, 10), dtype=bool)

        iou = SegmentationMetrics.iou(pred, target)
        assert iou > 0.99

    def test_iou_no_overlap(self):
        """Test IoU with no overlap."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[:5, :] = True
        target = np.zeros((10, 10), dtype=bool)
        target[5:, :] = True

        iou = SegmentationMetrics.iou(pred, target)
        assert iou < 0.01

    def test_precision(self):
        """Test precision calculation."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[0:5, 0:5] = True  # 25 predictions
        target = np.zeros((10, 10), dtype=bool)
        target[0:5, 0:10] = True  # 50 ground truth

        # TP = 25, FP = 0, so precision should be high
        precision = SegmentationMetrics.precision(pred, target)
        assert precision > 0.99

    def test_recall(self):
        """Test recall calculation."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[0:5, 0:5] = True  # 25 predictions
        target = np.zeros((10, 10), dtype=bool)
        target[0:5, 0:10] = True  # 50 ground truth

        # TP = 25, FN = 25, so recall should be ~0.5
        recall = SegmentationMetrics.recall(pred, target)
        assert 0.4 < recall < 0.6

    def test_specificity(self):
        """Test specificity calculation."""
        pred = np.zeros((10, 10), dtype=bool)
        pred[0:2, 0:2] = True  # Few predictions
        target = np.zeros((10, 10), dtype=bool)
        target[0:2, 0:2] = True  # Same as prediction

        # All true negatives are correctly identified
        specificity = SegmentationMetrics.specificity(pred, target)
        assert specificity > 0.99

    def test_hausdorff_distance_same_mask(self):
        """Test Hausdorff distance for identical masks."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for Hausdorff distance")

        mask = np.zeros((20, 20), dtype=bool)
        mask[5:15, 5:15] = True

        hd = SegmentationMetrics.hausdorff_distance(mask, mask)
        assert hd == 0.0

    def test_hausdorff_distance_empty_mask(self):
        """Test Hausdorff distance with empty mask."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for Hausdorff distance")

        pred = np.zeros((10, 10), dtype=bool)
        target = np.ones((10, 10), dtype=bool)

        hd = SegmentationMetrics.hausdorff_distance(pred, target)
        assert hd == float('inf')

    def test_average_surface_distance(self):
        """Test average surface distance calculation."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for surface distance")

        mask = np.zeros((20, 20), dtype=bool)
        mask[5:15, 5:15] = True

        asd = SegmentationMetrics.average_surface_distance(mask, mask)
        assert asd == 0.0

    def test_evaluate_all_metrics(self):
        """Test evaluating all metrics at once."""
        pred = np.zeros((20, 20), dtype=bool)
        pred[5:15, 5:15] = True
        target = np.zeros((20, 20), dtype=bool)
        target[7:17, 7:17] = True

        metrics = SegmentationMetrics.evaluate(
            pred, target,
            include_surface_metrics=SCIPY_AVAILABLE
        )

        assert "dice" in metrics
        assert "iou" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "specificity" in metrics

        if SCIPY_AVAILABLE:
            assert "hausdorff_distance" in metrics
            assert "average_surface_distance" in metrics


class TestSegmentationPostProcessor:
    """Tests for SegmentationPostProcessor class."""

    def test_processor_initialization(self):
        """Test post-processor initialization."""
        processor = SegmentationPostProcessor()
        assert processor.config is not None
        assert processor.config.threshold == 0.5

    def test_processor_with_custom_config(self):
        """Test post-processor with custom config."""
        config = SegmentationConfig(threshold=0.7, min_object_size=50)
        processor = SegmentationPostProcessor(config)
        assert processor.config.threshold == 0.7
        assert processor.config.min_object_size == 50

    def test_process_thresholding(self):
        """Test basic thresholding in process."""
        processor = SegmentationPostProcessor(
            SegmentationConfig(apply_post_processing=False)
        )

        prob_map = np.array([
            [0.3, 0.6, 0.8],
            [0.4, 0.5, 0.7],
            [0.2, 0.9, 0.1]
        ], dtype=np.float32)

        mask, regions = processor.process(prob_map, threshold=0.5)

        # Check threshold applied correctly
        expected = np.array([
            [0, 1, 1],
            [0, 0, 1],
            [0, 1, 0]
        ], dtype=np.uint8)

        np.testing.assert_array_equal(mask, expected)

    def test_fill_holes(self):
        """Test hole filling."""
        if not SCIPY_AVAILABLE and not SKIMAGE_AVAILABLE:
            pytest.skip("scipy or scikit-image required")

        processor = SegmentationPostProcessor()

        # Create mask with hole
        mask = np.ones((10, 10), dtype=bool)
        mask[4:6, 4:6] = False  # Hole in center

        filled = processor.fill_holes(mask)

        # Hole should be filled
        assert filled[5, 5] == True

    def test_remove_small_objects(self):
        """Test small object removal."""
        if not SCIPY_AVAILABLE and not SKIMAGE_AVAILABLE:
            pytest.skip("scipy or scikit-image required")

        processor = SegmentationPostProcessor()

        # Create mask with large and small regions
        mask = np.zeros((20, 20), dtype=bool)
        mask[2:8, 2:8] = True  # Large region (36 pixels)
        mask[15:17, 15:17] = True  # Small region (4 pixels)

        cleaned = processor.remove_small_objects(mask, min_size=10)

        # Large region should remain
        assert cleaned[5, 5] == True
        # Small region should be removed
        assert cleaned[16, 16] == False

    def test_apply_morphology_close(self):
        """Test morphological closing."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for morphology")

        processor = SegmentationPostProcessor()

        # Create mask with small gap
        mask = np.zeros((10, 10), dtype=bool)
        mask[3:7, 3:4] = True
        mask[3:7, 6:7] = True

        closed = processor.apply_morphology(mask, operation='close', kernel_size=3)

        # Closing should fill the gap
        assert isinstance(closed, np.ndarray)

    def test_apply_morphology_open(self):
        """Test morphological opening."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for morphology")

        processor = SegmentationPostProcessor()
        mask = np.zeros((10, 10), dtype=bool)
        mask[3:7, 3:7] = True

        opened = processor.apply_morphology(mask, operation='open', kernel_size=3)
        assert isinstance(opened, np.ndarray)

    def test_apply_morphology_dilate(self):
        """Test morphological dilation."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for morphology")

        processor = SegmentationPostProcessor()
        mask = np.zeros((10, 10), dtype=bool)
        mask[4:6, 4:6] = True

        dilated = processor.apply_morphology(mask, operation='dilate', kernel_size=3)

        # Dilated region should be larger
        assert np.sum(dilated) > np.sum(mask)

    def test_apply_morphology_erode(self):
        """Test morphological erosion."""
        if not SCIPY_AVAILABLE:
            pytest.skip("scipy required for morphology")

        processor = SegmentationPostProcessor()
        mask = np.zeros((10, 10), dtype=bool)
        mask[2:8, 2:8] = True

        eroded = processor.apply_morphology(mask, operation='erode', kernel_size=3)

        # Eroded region should be smaller
        assert np.sum(eroded) < np.sum(mask)


class TestCheckSegmentationAvailable:
    """Tests for availability check function."""

    def test_check_returns_dict(self):
        """Test that availability check returns proper dict."""
        result = check_segmentation_available()

        assert isinstance(result, dict)
        assert "pytorch" in result
        assert "scipy" in result
        assert "scikit-image" in result
        assert "gpu" in result

    def test_check_values_are_boolean(self):
        """Test that all values are boolean."""
        result = check_segmentation_available()

        for key, value in result.items():
            assert isinstance(value, bool), f"{key} should be boolean"


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestUNetModels:
    """Tests for U-Net model architectures (requires PyTorch)."""

    def test_standard_unet_forward(self):
        """Test standard U-Net forward pass."""
        from src.unet_segmentation import UNet
        import torch

        model = UNet(in_channels=1, out_channels=1, base_features=32)
        model.eval()

        # Create dummy input
        x = torch.randn(1, 1, 256, 256)

        with torch.no_grad():
            output = model(x)

        assert output.shape == (1, 1, 256, 256)

    def test_attention_unet_forward(self):
        """Test Attention U-Net forward pass."""
        from src.unet_segmentation import AttentionUNet
        import torch

        model = AttentionUNet(in_channels=1, out_channels=1, base_features=32)
        model.eval()

        x = torch.randn(1, 1, 256, 256)

        with torch.no_grad():
            output = model(x)

        assert output.shape == (1, 1, 256, 256)

    def test_residual_unet_forward(self):
        """Test Residual U-Net forward pass."""
        from src.unet_segmentation import ResidualUNet
        import torch

        model = ResidualUNet(in_channels=1, out_channels=1, base_features=32)
        model.eval()

        x = torch.randn(1, 1, 256, 256)

        with torch.no_grad():
            output = model(x)

        assert output.shape == (1, 1, 256, 256)

    def test_unet_multi_channel(self):
        """Test U-Net with multiple input/output channels."""
        from src.unet_segmentation import UNet
        import torch

        model = UNet(in_channels=3, out_channels=2, base_features=32)
        model.eval()

        x = torch.randn(2, 3, 128, 128)  # Batch of 2

        with torch.no_grad():
            output = model(x)

        assert output.shape == (2, 2, 128, 128)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestLossFunctions:
    """Tests for segmentation loss functions (requires PyTorch)."""

    def test_dice_loss(self):
        """Test Dice loss computation."""
        from src.unet_segmentation import DiceLoss
        import torch

        loss_fn = DiceLoss()

        # Perfect prediction
        pred = torch.ones(1, 1, 10, 10) * 10  # High logits
        target = torch.ones(1, 1, 10, 10)

        loss = loss_fn(pred, target)
        assert loss.item() < 0.1  # Should be close to 0

    def test_bce_dice_loss(self):
        """Test combined BCE + Dice loss."""
        from src.unet_segmentation import BCEDiceLoss
        import torch

        loss_fn = BCEDiceLoss(bce_weight=0.5, dice_weight=0.5)

        pred = torch.randn(1, 1, 10, 10)
        target = torch.randint(0, 2, (1, 1, 10, 10)).float()

        loss = loss_fn(pred, target)
        assert loss.item() > 0

    def test_focal_loss(self):
        """Test Focal loss computation."""
        from src.unet_segmentation import FocalLoss
        import torch

        loss_fn = FocalLoss(alpha=0.25, gamma=2.0)

        pred = torch.randn(1, 1, 10, 10)
        target = torch.randint(0, 2, (1, 1, 10, 10)).float()

        loss = loss_fn(pred, target)
        assert loss.item() > 0


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestUNetSegmentationPipeline:
    """Tests for the UNetSegmentation inference pipeline."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        from src.unet_segmentation import UNetSegmentation

        pipeline = UNetSegmentation()

        assert pipeline.config is not None
        assert pipeline.device is not None
        assert pipeline.post_processor is not None

    def test_pipeline_with_custom_config(self):
        """Test pipeline with custom configuration."""
        from src.unet_segmentation import UNetSegmentation

        config = SegmentationConfig(
            variant=UNetVariant.ATTENTION,
            input_size=(128, 128),
            threshold=0.6
        )

        pipeline = UNetSegmentation(config)

        assert pipeline.config.variant == UNetVariant.ATTENTION
        assert pipeline.config.input_size == (128, 128)
        assert pipeline.config.threshold == 0.6

    def test_create_model(self):
        """Test model creation."""
        from src.unet_segmentation import UNetSegmentation

        pipeline = UNetSegmentation()
        pipeline.create_model(UNetVariant.STANDARD)

        assert pipeline.model is not None

    def test_segment_single_image(self):
        """Test segmenting a single image."""
        from src.unet_segmentation import UNetSegmentation

        config = SegmentationConfig(
            input_size=(64, 64),
            base_features=16,
            use_gpu=False
        )
        pipeline = UNetSegmentation(config)
        pipeline.create_model()

        # Create test image
        image = np.random.rand(64, 64).astype(np.float32)

        result = pipeline.segment(image)

        assert isinstance(result, SegmentationResult)
        assert result.mask.shape == (64, 64)
        assert result.probability_map.shape == (64, 64)
        assert result.original_shape == (64, 64)

    def test_segment_volume(self):
        """Test segmenting a 3D volume."""
        from src.unet_segmentation import UNetSegmentation

        config = SegmentationConfig(
            input_size=(32, 32),
            base_features=16,
            use_gpu=False
        )
        pipeline = UNetSegmentation(config)
        pipeline.create_model()

        # Create test volume (5 slices)
        volume = np.random.rand(5, 32, 32).astype(np.float32)

        results = pipeline.segment_volume(volume, aggregate_3d=False)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, SegmentationResult)
            assert result.mask.shape == (32, 32)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")
class TestCreateUNetModel:
    """Tests for the factory function."""

    def test_create_standard_unet(self):
        """Test creating standard U-Net."""
        from src.unet_segmentation import create_unet_model, UNet

        model = create_unet_model('standard')
        assert isinstance(model, UNet)

    def test_create_attention_unet(self):
        """Test creating Attention U-Net."""
        from src.unet_segmentation import create_unet_model, AttentionUNet

        model = create_unet_model('attention')
        assert isinstance(model, AttentionUNet)

    def test_create_residual_unet(self):
        """Test creating Residual U-Net."""
        from src.unet_segmentation import create_unet_model, ResidualUNet

        model = create_unet_model('residual')
        assert isinstance(model, ResidualUNet)

    def test_create_with_custom_params(self):
        """Test creating model with custom parameters."""
        from src.unet_segmentation import create_unet_model

        model = create_unet_model(
            'standard',
            in_channels=3,
            out_channels=5,
            base_features=32
        )

        assert model.in_channels == 3
        assert model.out_channels == 5

    def test_create_invalid_variant(self):
        """Test error on invalid variant."""
        from src.unet_segmentation import create_unet_model

        with pytest.raises(ValueError, match="Unknown variant"):
            create_unet_model('invalid_variant')


class TestUNetSegmentationWithoutTorch:
    """Tests for behavior when PyTorch is not available."""

    def test_pipeline_raises_without_torch(self):
        """Test that pipeline raises error without PyTorch."""
        if TORCH_AVAILABLE:
            pytest.skip("Test only relevant when PyTorch not installed")

        from src.unet_segmentation import UNetSegmentation

        with pytest.raises(RuntimeError, match="PyTorch required"):
            UNetSegmentation()

    def test_create_model_raises_without_torch(self):
        """Test that create_unet_model raises without PyTorch."""
        if TORCH_AVAILABLE:
            pytest.skip("Test only relevant when PyTorch not installed")

        from src.unet_segmentation import create_unet_model

        with pytest.raises(RuntimeError, match="PyTorch required"):
            create_unet_model('standard')
