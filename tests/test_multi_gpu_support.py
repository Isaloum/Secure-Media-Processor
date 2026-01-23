"""Tests for multi-GPU backend support."""

import pytest
import torch
from unittest.mock import patch, MagicMock
from src.gpu_processor import GPUMediaProcessor


class TestMultiGPUSupport:
    """Test GPU detection and selection across different backends."""

    def test_nvidia_cuda_detection(self):
        """Test NVIDIA CUDA GPU detection."""
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.get_device_name', return_value='NVIDIA GeForce RTX 3080'), \
             patch('torch.cuda.get_device_properties') as mock_props:

            mock_props.return_value = MagicMock(total_memory=10 * 1024**3)  # 10GB

            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.gpu_enabled is True
            assert processor.device_type == 'cuda'
            assert 'NVIDIA' in processor.device_name or 'RTX' in processor.device_name
            assert str(processor.device).startswith('cuda')

    def test_apple_metal_detection(self):
        """Test Apple Metal (M1/M2/M3) GPU detection."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=True):

            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.gpu_enabled is True
            assert processor.device_type == 'mps'
            assert 'Apple' in processor.device_name
            assert str(processor.device) == 'mps'

    def test_intel_xpu_detection(self):
        """Test Intel oneAPI (Arc GPU) detection."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=False), \
             patch('torch.xpu.is_available', return_value=True):

            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.gpu_enabled is True
            assert processor.device_type == 'xpu'
            assert 'Intel' in processor.device_name
            assert str(processor.device).startswith('xpu')

    def test_amd_rocm_detection(self):
        """Test AMD ROCm GPU detection."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=False), \
             patch('torch.xpu.is_available', return_value=False), \
             patch('torch.version.hip', '5.4.0'):

            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.gpu_enabled is True
            assert processor.device_type == 'rocm'
            assert 'AMD' in processor.device_name

    def test_cpu_fallback_no_gpu(self):
        """Test CPU fallback when no GPU is available."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=False), \
             patch('torch.xpu.is_available', return_value=False), \
             patch('torch.version.hip', None):

            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.gpu_enabled is False
            assert processor.device_type == 'cpu'
            assert str(processor.device) == 'cpu'

    def test_cpu_fallback_disabled(self):
        """Test CPU fallback when GPU is manually disabled."""
        processor = GPUMediaProcessor(gpu_enabled=False)

        assert processor.gpu_enabled is False
        assert processor.device_type == 'cpu'
        assert str(processor.device) == 'cpu'

    def test_gpu_priority_order(self):
        """Test that GPU detection follows correct priority order: CUDA > MPS > XPU > ROCm > CPU."""
        # When both CUDA and MPS available, CUDA wins
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.backends.mps.is_available', return_value=True), \
             patch('torch.cuda.get_device_name', return_value='NVIDIA RTX 4090'), \
             patch('torch.cuda.get_device_properties') as mock_props:

            mock_props.return_value = MagicMock(total_memory=24 * 1024**3)
            processor = GPUMediaProcessor(gpu_enabled=True)

            assert processor.device_type == 'cuda'

    def test_clear_gpu_cache_cuda(self):
        """Test GPU cache clearing for NVIDIA CUDA."""
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.get_device_name', return_value='NVIDIA RTX 3090'), \
             patch('torch.cuda.get_device_properties') as mock_props, \
             patch('torch.cuda.empty_cache') as mock_empty:

            mock_props.return_value = MagicMock(total_memory=24 * 1024**3)
            processor = GPUMediaProcessor(gpu_enabled=True)
            processor._clear_gpu_cache()

            mock_empty.assert_called_once()

    def test_clear_gpu_cache_mps(self):
        """Test GPU cache clearing for Apple Metal."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=True), \
             patch('torch.mps.empty_cache') as mock_empty:

            processor = GPUMediaProcessor(gpu_enabled=True)
            processor._clear_gpu_cache()

            # MPS cache clearing should be attempted
            mock_empty.assert_called_once()

    def test_device_info_cuda(self):
        """Test device info reporting for NVIDIA CUDA."""
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.get_device_name', return_value='NVIDIA GeForce RTX 4080'), \
             patch('torch.cuda.get_device_properties') as mock_props, \
             patch('torch.cuda.memory_allocated', return_value=2 * 1024**3), \
             patch('torch.cuda.memory_reserved', return_value=3 * 1024**3), \
             patch('torch.version.cuda', '12.1'):

            mock_props.return_value = MagicMock(total_memory=16 * 1024**3)
            processor = GPUMediaProcessor(gpu_enabled=True)
            info = processor.get_device_info()

            assert info['vendor'] == 'NVIDIA'
            assert info['backend'] == 'cuda'
            assert info['memory_total_gb'] == 16.0
            assert 'cuda_version' in info

    def test_device_info_mps(self):
        """Test device info reporting for Apple Metal."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=True):

            processor = GPUMediaProcessor(gpu_enabled=True)
            info = processor.get_device_info()

            assert info['vendor'] == 'Apple'
            assert info['backend'] == 'mps'
            assert info['architecture'] == 'Apple Silicon (M1/M2/M3)'

    def test_device_info_cpu(self):
        """Test device info reporting for CPU fallback."""
        with patch('torch.cuda.is_available', return_value=False), \
             patch('torch.backends.mps.is_available', return_value=False), \
             patch('torch.xpu.is_available', return_value=False), \
             patch('torch.version.hip', None):

            processor = GPUMediaProcessor(gpu_enabled=True)
            info = processor.get_device_info()

            assert info['backend'] == 'cpu'
            assert info['name'] == 'CPU Processing'

    def test_multi_gpu_device_selection(self):
        """Test device ID selection for multi-GPU systems."""
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.get_device_name') as mock_name, \
             patch('torch.cuda.get_device_properties') as mock_props:

            mock_name.return_value = 'NVIDIA RTX 3080'
            mock_props.return_value = MagicMock(total_memory=10 * 1024**3)

            # Test device 0
            processor0 = GPUMediaProcessor(gpu_enabled=True, device_id=0)
            assert str(processor0.device) == 'cuda:0'

            # Test device 1
            processor1 = GPUMediaProcessor(gpu_enabled=True, device_id=1)
            assert str(processor1.device) == 'cuda:1'

    def test_gpu_disabled_by_user(self):
        """Test that GPU can be manually disabled even when available."""
        with patch('torch.cuda.is_available', return_value=True):
            processor = GPUMediaProcessor(gpu_enabled=False)

            assert processor.gpu_enabled is False
            assert str(processor.device) == 'cpu'
