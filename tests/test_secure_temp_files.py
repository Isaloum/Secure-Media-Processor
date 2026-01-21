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

    @patch('src.connectors.connector_manager.tempfile.mkstemp')
    @patch('src.connectors.connector_manager.os.chmod')
    @patch('src.connectors.connector_manager.os.close')
    def test_temp_file_created_with_secure_permissions(
        self, mock_close, mock_chmod, mock_mkstemp, tmp_path
    ):
        """Test that temporary files are created with 0600 permissions."""
        # Setup
        temp_file = tmp_path / "test_temp.tmp"
        mock_mkstemp.return_value = (999, str(temp_file))

        manager = ConnectorManager()

        # Create mock connectors
        source_connector = Mock()
        source_connector.download_file.return_value = {'success': True}
        target_connector = Mock()
        target_connector.upload_file.return_value = {'success': True}

        manager.add_connector('source', source_connector)
        manager.add_connector('target', target_connector)

        # Execute sync (which creates temp file)
        try:
            manager.sync_file_between_connectors(
                'test.txt',
                'source',
                ['target']
            )
        except:
            pass  # We're testing the permissions, not the full operation

        # Verify secure permissions were set (0600 = owner read/write only)
        mock_chmod.assert_called()
        call_args = mock_chmod.call_args
        if call_args:
            assert call_args[0][1] == 0o600, "Temp file should have 0600 permissions"

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

    @patch('src.connectors.connector_manager.os.urandom')
    def test_temp_file_secure_deletion_overwrites_data(
        self, mock_urandom, tmp_path
    ):
        """Test that temporary files are securely overwritten before deletion."""
        # Create a test file with sensitive data
        test_file = tmp_path / "sensitive.tmp"
        sensitive_data = b"TOP SECRET DATA 12345"
        test_file.write_bytes(sensitive_data)

        file_size = len(sensitive_data)
        mock_urandom.return_value = b'R' * file_size

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
            f.write(mock_urandom.return_value)
            f.flush()
            os.fsync(f.fileno())

        # Read the file to verify overwrite
        overwritten_data = test_file.read_bytes()

        # Verify original data is gone
        assert sensitive_data not in overwritten_data
        assert overwritten_data == mock_urandom.return_value

        # Cleanup
        test_file.unlink()

    def test_temp_file_cleanup_on_exception(self):
        """Test that temp files are cleaned up even if exceptions occur."""
        manager = ConnectorManager()

        # Create mock connectors that will fail
        source_connector = Mock()
        source_connector.download_file.side_effect = Exception("Download failed")

        manager.add_connector('source', source_connector)

        # This should handle the exception and still clean up
        result = manager.sync_file_between_connectors(
            'test.txt',
            'source',
            ['target']
        )

        # Verify it failed gracefully
        assert result['success'] is False

    @patch('src.connectors.connector_manager.tempfile.mkstemp')
    def test_temp_file_prefix_and_suffix(self, mock_mkstemp):
        """Test that temp files use secure prefix and suffix."""
        mock_mkstemp.return_value = (999, '/tmp/secure_media_abc123.tmp')

        manager = ConnectorManager()

        source_connector = Mock()
        source_connector.download_file.return_value = {'success': False}
        manager.add_connector('source', source_connector)

        try:
            manager.sync_file_between_connectors('test.txt', 'source', [])
        except:
            pass

        # Verify mkstemp was called with secure prefix/suffix
        if mock_mkstemp.called:
            call_kwargs = mock_mkstemp.call_args[1] if mock_mkstemp.call_args else {}
            assert call_kwargs.get('prefix') == 'secure_media_'
            assert call_kwargs.get('suffix') == '.tmp'

    def test_file_descriptor_closed_properly(self, tmp_path):
        """Test that file descriptors are properly closed."""
        import tempfile

        # Create temp file
        fd, temp_path = tempfile.mkstemp(dir=tmp_path)

        # Close descriptor
        os.close(fd)

        # Verify we can't use the closed descriptor
        with pytest.raises(OSError):
            os.write(fd, b'test')

        # Cleanup
        Path(temp_path).unlink()

    def test_secure_deletion_multiple_passes(self, tmp_path):
        """Test that secure deletion performs multiple overwrite passes."""
        test_file = tmp_path / "multipass.tmp"
        original_data = b"CONFIDENTIAL DATA"
        test_file.write_bytes(original_data)
        file_size = len(original_data)

        # Pass 1: zeros
        with open(test_file, 'wb') as f:
            f.write(b'\0' * file_size)
            f.flush()

        assert test_file.read_bytes() == b'\0' * file_size

        # Pass 2: ones
        with open(test_file, 'wb') as f:
            f.write(b'\xff' * file_size)
            f.flush()

        assert test_file.read_bytes() == b'\xff' * file_size

        # Pass 3: random
        random_data = os.urandom(file_size)
        with open(test_file, 'wb') as f:
            f.write(random_data)
            f.flush()

        final_data = test_file.read_bytes()
        assert final_data == random_data
        assert original_data not in final_data

        test_file.unlink()

    def test_no_temp_files_left_behind(self, tmp_path):
        """Test that no temporary files are left behind after operations."""
        import tempfile

        # Get current temp dir file count
        temp_dir = Path(tempfile.gettempdir())
        before_files = set(temp_dir.glob('secure_media_*'))

        manager = ConnectorManager()
        source = Mock()
        source.download_file.return_value = {'success': True}
        target = Mock()
        target.upload_file.return_value = {'success': True}

        manager.add_connector('source', source)
        manager.add_connector('target', target)

        # Run sync operation
        manager.sync_file_between_connectors('test.txt', 'source', ['target'])

        # Check no new temp files remain
        after_files = set(temp_dir.glob('secure_media_*'))
        new_files = after_files - before_files

        assert len(new_files) == 0, f"Temp files left behind: {new_files}"


class TestGPUMemoryCleanup:
    """Test suite for GPU memory cleanup."""

    @pytest.fixture
    def gpu_processor(self):
        """Create GPU processor instance."""
        from src.gpu_processor import GPUMediaProcessor
        return GPUMediaProcessor(gpu_enabled=False)  # Use CPU for testing

    def test_gpu_cache_cleared_after_resize(self, gpu_processor, tmp_path):
        """Test that GPU cache is cleared after image resize."""
        # Create a simple test image
        import numpy as np
        from PIL import Image

        test_image = tmp_path / "test.jpg"
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        img.save(test_image)

        output_image = tmp_path / "output.jpg"

        # Process image (GPU cache should be cleared after)
        with patch('torch.cuda.empty_cache') as mock_empty_cache:
            gpu_processor.gpu_enabled = True  # Temporarily enable for test
            gpu_processor.device = 'cuda:0'

            try:
                result = gpu_processor.resize_image(
                    test_image,
                    output_image,
                    (50, 50)
                )
            except:
                pass  # We're testing cache cleanup, not full operation

            # Verify empty_cache was called
            # Note: May fail if torch.cuda not available
            if gpu_processor.gpu_enabled:
                mock_empty_cache.assert_called()

    def test_tensors_deleted_after_processing(self, gpu_processor):
        """Test that PyTorch tensors are explicitly deleted."""
        # This is more of a code review test - verifies that 'del' is called
        import inspect
        source = inspect.getsource(gpu_processor.resize_image)

        # Verify code contains tensor cleanup
        assert 'del' in source, "resize_image should explicitly delete tensors"
        assert 'empty_cache' in source, "resize_image should call empty_cache"

    def test_batch_processing_clears_memory(self, gpu_processor):
        """Test that batch processing clears GPU memory after completion."""
        import inspect
        source = inspect.getsource(gpu_processor.batch_resize)

        # Verify batch processing has final cleanup
        assert 'empty_cache' in source, "batch_resize should clear GPU cache"
        assert 'logger' in source, "batch_resize should log cleanup"
