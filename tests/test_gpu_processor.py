"""Test suite for GPU processor module."""

import pytest
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image

# Skip all tests in this module if torch is not available
torch = pytest.importorskip("torch")

from src.gpu_processor import GPUMediaProcessor


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample image for testing."""
    img = Image.new('RGB', (800, 600), color='red')
    img_path = temp_dir / "sample.jpg"
    img.save(img_path)
    return img_path


@pytest.fixture
def processor():
    """Create GPU processor instance."""
    return GPUMediaProcessor(gpu_enabled=torch.cuda.is_available())


def test_device_initialization():
    """Test device initialization."""
    processor = GPUMediaProcessor(gpu_enabled=False)
    assert processor.device == torch.device('cpu')
    
    if torch.cuda.is_available():
        gpu_processor = GPUMediaProcessor(gpu_enabled=True)
        assert 'cuda' in str(gpu_processor.device)


def test_resize_image(processor, sample_image, temp_dir):
    """Test image resizing."""
    output_path = temp_dir / "resized.jpg"
    
    result = processor.resize_image(
        sample_image,
        output_path,
        size=(400, 300)
    )
    
    assert output_path.exists()
    assert result['original_size'] == (800, 600)
    assert result['new_size'][0] <= 400
    assert result['new_size'][1] <= 300


def test_batch_resize(processor, temp_dir):
    """Test batch image resizing."""
    # Create multiple test images
    image_paths = []
    for i in range(3):
        img = Image.new('RGB', (800, 600), color=('red', 'green', 'blue')[i])
        img_path = temp_dir / f"image{i}.jpg"
        img.save(img_path)
        image_paths.append(img_path)
    
    output_dir = temp_dir / "resized"
    
    result = processor.batch_resize(
        image_paths,
        output_dir,
        size=(400, 300)
    )
    
    assert result['total'] == 3
    assert result['processed'] == 3
    assert result['failed'] == 0
    assert len(list(output_dir.glob('*.jpg'))) == 3


def test_apply_filter(processor, sample_image, temp_dir):
    """Test applying filters to images."""
    output_path = temp_dir / "filtered.jpg"
    
    result = processor.apply_filter(
        sample_image,
        output_path,
        filter_type='blur',
        intensity=1.0
    )
    
    assert output_path.exists()
    assert result['filter_type'] == 'blur'
    assert result['intensity'] == 1.0


def test_get_device_info(processor):
    """Test getting device information."""
    info = processor.get_device_info()
    
    assert 'device' in info
    assert 'name' in info
    assert info['device'] in ['CPU', 'GPU']
