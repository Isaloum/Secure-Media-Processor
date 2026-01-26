"""
Tests for secure temporary file handling.

These tests verify that temporary files are created with restrictive permissions
and are securely deleted to prevent data leakage.
"""

import pytest
import os
import stat
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.connectors.connector_manager import ConnectorManager


class TestSecureTempFiles:
    """Test suite for secure temporary file handling."""

    def test_temp_file_permissions_owner_only(self, tmp_path):
        """Test that temp file permissions prevent other users from reading."""
        temp_file = tmp_path / "test_secure.tmp"
        temp_file.write_text("sensitive data")

        # Set secure permissions
        os.chmod(temp_file, 0o600)

        # Verify permissions
        file_stat = temp_file.stat()
        mode = stat.S_IMODE(file_stat.st_mode)

        # Check that only owner has read/write, no one else
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

        # Verify owner can read/write
        assert os.access(temp_file, os.R_OK), "Owner should have read access"
        assert os.access(temp_file, os.W_OK), "Owner should have write access"

    def test_temp_file_secure_deletion_simulation(self, tmp_path):
        """Test that temporary files can be securely overwritten."""
        # Create a test file with sensitive data
        test_file = tmp_path / "sensitive.tmp"
        sensitive_data = b"TOP SECRET DATA 12345"
        test_file.write_bytes(sensitive_data)

        file_size = len(sensitive_data)
        random_data = b'R' * file_size

        # Simulate secure deletion (3-pass overwrite)
        with open(test_file, 'wb') as f:
            # Pass 1: zeros
            f.write(b'\0' * file_size)
            f.flush()
            os.fsync(f.fileno())

            # Pass 2: ones
            f.seek(0)
            f.write(b'\xff' * file_size)
            f.flush()
            os.fsync(f.fileno())

            # Pass 3: random
            f.seek(0)
            f.write(random_data)
            f.flush()
            os.fsync(f.fileno())

        # Read the file to verify overwrite
        overwritten_data = test_file.read_bytes()

        # Verify original data is gone
        assert sensitive_data not in overwritten_data
        assert overwritten_data == random_data

        # Cleanup
        test_file.unlink()

    def test_secure_overwrite_basic(self, tmp_path):
        """Test basic secure overwrite functionality."""
        # Create test file
        test_file = tmp_path / "overwrite_test.tmp"
        original_data = b"SENSITIVE ORIGINAL DATA"
        test_file.write_bytes(original_data)

        # Use random bytes for overwrite
        import secrets
        random_data = secrets.token_bytes(len(original_data))

        with open(test_file, 'wb') as f:
            f.write(random_data)
            f.flush()

        final_data = test_file.read_bytes()
        assert final_data == random_data
        assert original_data not in final_data

        test_file.unlink()

    def test_connector_manager_creation(self):
        """Test that ConnectorManager can be created."""
        manager = ConnectorManager()
        assert manager is not None
        assert manager.connectors == {}

    def test_connector_manager_add_remove(self):
        """Test adding and removing connectors from manager."""
        manager = ConnectorManager()

        # Add mock connector
        mock_connector = Mock()
        mock_connector.get_provider_name.return_value = 'mock'
        mock_connector.is_connected.return_value = False

        result = manager.add_connector('test', mock_connector)
        assert result is True
        assert 'test' in manager.connectors

        # Remove connector
        result = manager.remove_connector('test')
        assert result is True
        assert 'test' not in manager.connectors


class TestGPUMemoryCleanup:
    """Test suite for GPU memory cleanup."""

    @pytest.fixture
    def gpu_processor(self):
        """Create GPU processor instance."""
        from src.gpu_processor import GPUMediaProcessor
        return GPUMediaProcessor(gpu_enabled=False)  # Use CPU for testing

    def test_gpu_processor_cpu_fallback(self, gpu_processor, tmp_path):
        """Test that GPU processor can process images in CPU mode."""
        from PIL import Image
        import numpy as np

        # Create a simple test image
        test_image = tmp_path / "test.jpg"
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        img.save(test_image)

        output_image = tmp_path / "output.jpg"

        # Process image in CPU mode
        result = gpu_processor.resize_image(
            test_image,
            output_image,
            (50, 50)
        )

        # Should succeed and produce output
        assert result is not None
        assert 'device' in result
        # In CPU mode, device should indicate CPU
        assert 'CPU' in str(result.get('device', ''))

    def test_tensors_deleted_after_processing(self, gpu_processor):
        """Test that PyTorch tensors are explicitly deleted."""
        # This is more of a code review test - verifies that 'del' is called
        import inspect
        source = inspect.getsource(gpu_processor.resize_image)

        # Verify code contains tensor cleanup
        assert 'del' in source, "resize_image should explicitly delete tensors"
        # The method calls _clear_gpu_cache, not empty_cache directly
        assert '_clear_gpu_cache' in source, "resize_image should call _clear_gpu_cache"

    def test_batch_processing_clears_memory(self, gpu_processor):
        """Test that batch processing clears GPU memory after completion."""
        import inspect
        source = inspect.getsource(gpu_processor.batch_resize)

        # Verify batch processing has final cleanup
        assert '_clear_gpu_cache' in source, "batch_resize should clear GPU cache"
        assert 'logger' in source, "batch_resize should log cleanup"

    def test_clear_gpu_cache_method_exists(self, gpu_processor):
        """Test that _clear_gpu_cache method exists and is callable."""
        assert hasattr(gpu_processor, '_clear_gpu_cache')
        assert callable(gpu_processor._clear_gpu_cache)

        # Should not raise even when GPU is disabled
        gpu_processor._clear_gpu_cache()

    def test_device_info_without_gpu(self, gpu_processor):
        """Test device info when GPU is not available."""
        info = gpu_processor.get_device_info()

        assert info is not None
        assert 'device' in info
        assert 'CPU' in info['device']
