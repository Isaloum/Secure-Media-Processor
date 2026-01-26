"""GPU-accelerated media processing module.

This module provides GPU-accelerated media processing using PyTorch.
PyTorch is optional - if not installed, the module will fall back to
CPU-only processing using OpenCV/Pillow.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Union, Optional, Tuple, List, TYPE_CHECKING
import logging

# Try to import torch - it's optional
try:
    import torch
    import torchvision.transforms as transforms
    from torchvision.io import read_image, write_jpeg, write_png
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    transforms = None

logger = logging.getLogger(__name__)

# PyTorch is optional - try to import, fall back gracefully
TORCH_AVAILABLE = False
torch = None
transforms = None
read_image = None
write_jpeg = None
write_png = None

try:
    import torch as _torch
    import torchvision.transforms as _transforms
    from torchvision.io import read_image as _read_image
    from torchvision.io import write_jpeg as _write_jpeg
    from torchvision.io import write_png as _write_png

    torch = _torch
    transforms = _transforms
    read_image = _read_image
    write_jpeg = _write_jpeg
    write_png = _write_png
    TORCH_AVAILABLE = True
    logger.debug("PyTorch available for GPU acceleration")
except ImportError:
    logger.info("PyTorch not installed - GPU acceleration disabled. Install with: pip install secure-media-processor[gpu]")


class GPUMediaProcessor:
    """Handle GPU-accelerated media processing operations.

    Supports multiple GPU backends:
    - NVIDIA CUDA (RTX/Tesla/Quadro)
    - Apple Metal (M1/M2/M3)
    - AMD ROCm (Radeon RX)
    - Intel oneAPI (Arc)

    Falls back to CPU-only processing via OpenCV/Pillow when PyTorch is not installed.
    """

    def __init__(self, gpu_enabled: bool = True, device_id: int = 0):
        """Initialize GPU processor with automatic device detection.

        Args:
            gpu_enabled: Whether to use GPU acceleration.
            device_id: Device ID to use (for multi-GPU systems).
        """
        self.gpu_enabled = False
        self.device_type = 'cpu'
        self.device_name = 'CPU Processing'
        claude/setup-production-fullstack-NWyrz
        self.device = None

        # Check if torch is available
        if not TORCH_AVAILABLE:
            logger.warning("⚠️  PyTorch not installed. GPU acceleration disabled.")
            logger.info("To enable GPU support: pip install secure-media-processor[gpu]")

        self.device = None  # Will be set if torch is available
        self._torch_available = TORCH_AVAILABLE

        # If PyTorch not available, fall back to CPU-only mode
        if not TORCH_AVAILABLE:
            logger.info("PyTorch not installed, using CPU-only processing via OpenCV/Pillow") 
        main
            return

        if not gpu_enabled:
            self.device = torch.device('cpu')
            logger.info("GPU disabled by user, using CPU")
            return

        # Try NVIDIA CUDA first (most common)
        if torch.cuda.is_available():
            self.device = torch.device(f'cuda:{device_id}')
            self.gpu_enabled = True
            self.device_type = 'cuda'
            self.device_name = torch.cuda.get_device_name(device_id)
            gpu_memory = torch.cuda.get_device_properties(device_id).total_memory / 1e9
            logger.info(f"NVIDIA GPU detected: {self.device_name}")
            logger.info(f"GPU memory: {gpu_memory:.2f} GB")

        # Try Apple Metal (M1/M2/M3 Macs)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = torch.device('mps')
            self.gpu_enabled = True
            self.device_type = 'mps'
            self.device_name = 'Apple Metal GPU'
            logger.info(f"Apple Metal GPU detected: {self.device_name}")
            logger.info("Apple Silicon unified memory")

        # Try Intel oneAPI (Arc GPUs)
        elif hasattr(torch, 'xpu') and torch.xpu.is_available():
            self.device = torch.device(f'xpu:{device_id}')
            self.gpu_enabled = True
            self.device_type = 'xpu'
            self.device_name = f'Intel XPU {device_id}'
            logger.info(f"Intel GPU detected: {self.device_name}")

        # Try AMD ROCm (if available)
        elif hasattr(torch.version, 'hip') and torch.version.hip is not None:
            # ROCm uses CUDA-compatible API
            self.device = torch.device(f'cuda:{device_id}')
            self.gpu_enabled = True
            self.device_type = 'rocm'
            self.device_name = 'AMD ROCm GPU'
            logger.info(f"AMD GPU detected: {self.device_name}")

        # Fallback to CPU
        else:
            self.device = torch.device('cpu')
            logger.info("No GPU detected, using CPU")
            logger.info("Supported GPUs: NVIDIA (CUDA), Apple (Metal), AMD (ROCm), Intel (Arc)")

    def _check_torch_available(self):
        """Check if PyTorch is available and raise helpful error if not."""
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is required for GPU-accelerated media processing.\n"
                "Install it with: pip install secure-media-processor[gpu]\n"
                "Or: pip install -r requirements-gpu.txt"
            )

    def _clear_gpu_cache(self):
        """Clear GPU memory cache based on device type."""
        if not self.gpu_enabled or not self._torch_available:
            return

        if self.device_type == 'cuda' or self.device_type == 'rocm':
            torch.cuda.empty_cache()
        elif self.device_type == 'mps':
            if hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()
        elif self.device_type == 'xpu':
            if hasattr(torch.xpu, 'empty_cache'):
                torch.xpu.empty_cache()
    
    def resize_image(self,
                     input_path: Union[str, Path],
                     output_path: Union[str, Path],
                     size: Tuple[int, int],
                     maintain_aspect_ratio: bool = True) -> dict:
claude/setup-production-fullstack-NWyrz
        """Resize an image using GPU acceleration.

        """Resize an image using GPU acceleration (or CPU fallback).
main

        Args:
            input_path: Path to input image.
            output_path: Path to save resized image.
            size: Target size (width, height).
            maintain_aspect_ratio: Whether to maintain aspect ratio.

        Returns:
            Dictionary containing processing metadata.
        """
        self._check_torch_available()

        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use CPU fallback with Pillow if PyTorch not available
        if not self._torch_available:
            return self._resize_image_cpu(input_path, output_path, size, maintain_aspect_ratio)

        # Read image and move to device
        image = read_image(str(input_path)).to(self.device)
        original_size = (image.shape[2], image.shape[1])

        # Create transform
        if maintain_aspect_ratio:
            transform = transforms.Resize(size, antialias=True)
        else:
            transform = transforms.Resize(size, antialias=True)

        # Process image
        resized = transform(image)

        # Save image
        if output_path.suffix.lower() in ['.jpg', '.jpeg']:
            write_jpeg(resized.cpu(), str(output_path), quality=95)
        else:
            write_png(resized.cpu(), str(output_path))

        # Store results before cleanup
        result = {
            'original_size': original_size,
            'new_size': (resized.shape[2], resized.shape[1]),
            'device': str(self.device),
            'output_path': str(output_path)
        }

        # Clear GPU memory to prevent memory leaks
        del image, resized
        self._clear_gpu_cache()

        return result

    def _resize_image_cpu(self,
                          input_path: Path,
                          output_path: Path,
                          size: Tuple[int, int],
                          maintain_aspect_ratio: bool) -> dict:
        """CPU fallback for image resizing using Pillow."""
        from PIL import Image

        with Image.open(input_path) as img:
            original_size = img.size

            if maintain_aspect_ratio:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                new_size = img.size
            else:
                img = img.resize(size, Image.Resampling.LANCZOS)
                new_size = size

            # Save with appropriate format
            if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                img.save(output_path, 'JPEG', quality=95)
            else:
                img.save(output_path, 'PNG')

        return {
            'original_size': original_size,
            'new_size': new_size,
            'device': 'CPU',
            'output_path': str(output_path)
        }
    
    def batch_resize(self,
                     input_paths: List[Union[str, Path]],
                     output_dir: Union[str, Path],
                     size: Tuple[int, int],
                     maintain_aspect_ratio: bool = True) -> dict:
        """Resize multiple images in batch using GPU.

        Args:
            input_paths: List of input image paths.
            output_dir: Directory to save resized images.
            size: Target size (width, height).
            maintain_aspect_ratio: Whether to maintain aspect ratio.

        Returns:
            Dictionary containing batch processing statistics.
        """
        self._check_torch_available()

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        processed = []
        failed = []
        
        for input_path in input_paths:
            input_path = Path(input_path)
            output_path = output_dir / input_path.name
            
            try:
                result = self.resize_image(
                    input_path,
                    output_path,
                    size,
                    maintain_aspect_ratio
                )
                processed.append(result)
            except Exception as e:
                logger.error(f"Failed to process {input_path}: {e}")
                failed.append({'file': str(input_path), 'error': str(e)})

        # Final GPU memory cleanup after batch processing
        self._clear_gpu_cache()
        if self.gpu_enabled:
            logger.debug(f"GPU memory freed after batch processing {len(processed)} images")

        return {
            'total': len(input_paths),
            'processed': len(processed),
            'failed': len(failed),
            'failed_files': failed
        }
    
    def apply_filter(self,
                     input_path: Union[str, Path],
                     output_path: Union[str, Path],
                     filter_type: str = 'blur',
                     intensity: float = 1.0) -> dict:
 claude/setup-production-fullstack-NWyrz
        """Apply filters to an image using GPU.

        """Apply filters to an image using GPU (or CPU fallback).
 main

        Args:
            input_path: Path to input image.
            output_path: Path to save filtered image.
            filter_type: Type of filter ('blur', 'sharpen', 'edge', 'denoise').
            intensity: Filter intensity (0.0 to 2.0).

        Returns:
            Dictionary containing processing metadata.
        """
        self._check_torch_available()

        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use CPU fallback with OpenCV/Pillow if PyTorch not available
        if not self._torch_available:
            return self._apply_filter_cpu(input_path, output_path, filter_type, intensity)

        # Read image
        image = read_image(str(input_path)).to(self.device).float() / 255.0

        # Apply filter based on type
        if filter_type == 'blur':
            transform = transforms.GaussianBlur(
                kernel_size=int(5 * intensity) | 1,  # Ensure odd
                sigma=intensity
            )
            filtered = transform(image)

        elif filter_type == 'sharpen':
            # Create sharpening kernel
            kernel = torch.tensor([
                [-1, -1, -1],
                [-1, 9, -1],
                [-1, -1, -1]
            ], dtype=torch.float32).to(self.device) * intensity

            # Apply convolution
            filtered = torch.nn.functional.conv2d(
                image.unsqueeze(0),
                kernel.unsqueeze(0).unsqueeze(0).repeat(3, 1, 1, 1),
                padding=1,
                groups=3
            ).squeeze(0)

        elif filter_type == 'edge':
            # Sobel edge detection
            sobel_x = torch.tensor([
                [-1, 0, 1],
                [-2, 0, 2],
                [-1, 0, 1]
            ], dtype=torch.float32).to(self.device)

            sobel_y = torch.tensor([
                [-1, -2, -1],
                [0, 0, 0],
                [1, 2, 1]
            ], dtype=torch.float32).to(self.device)

            edges_x = torch.nn.functional.conv2d(
                image.unsqueeze(0),
                sobel_x.unsqueeze(0).unsqueeze(0).repeat(3, 1, 1, 1),
                padding=1,
                groups=3
            )

            edges_y = torch.nn.functional.conv2d(
                image.unsqueeze(0),
                sobel_y.unsqueeze(0).unsqueeze(0).repeat(3, 1, 1, 1),
                padding=1,
                groups=3
            )

            filtered = (torch.sqrt(edges_x**2 + edges_y**2) * intensity).squeeze(0)

        else:
            filtered = image

        # Clamp values and convert back
        filtered = torch.clamp(filtered, 0, 1)
        filtered = (filtered * 255).byte()

        # Save image
        if output_path.suffix.lower() in ['.jpg', '.jpeg']:
            write_jpeg(filtered.cpu(), str(output_path), quality=95)
        else:
            write_png(filtered.cpu(), str(output_path))

        return {
            'filter_type': filter_type,
            'intensity': intensity,
            'device': str(self.device),
            'output_path': str(output_path)
        }

    def _apply_filter_cpu(self,
                          input_path: Path,
                          output_path: Path,
                          filter_type: str,
                          intensity: float) -> dict:
        """CPU fallback for image filtering using OpenCV/Pillow."""
        from PIL import Image, ImageFilter

        with Image.open(input_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            if filter_type == 'blur':
                # Gaussian blur
                radius = max(1, int(intensity * 2))
                filtered = img.filter(ImageFilter.GaussianBlur(radius=radius))

            elif filter_type == 'sharpen':
                # Apply sharpen filter (intensity controls number of applications)
                filtered = img
                applications = max(1, int(intensity))
                for _ in range(applications):
                    filtered = filtered.filter(ImageFilter.SHARPEN)

            elif filter_type == 'edge':
                # Edge detection using OpenCV
                img_array = np.array(img)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                # Convert back to RGB
                edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
                filtered = Image.fromarray((edges_rgb * intensity).astype(np.uint8))

            else:
                filtered = img

            # Save with appropriate format
            if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                filtered.save(output_path, 'JPEG', quality=95)
            else:
                filtered.save(output_path, 'PNG')

        return {
            'filter_type': filter_type,
            'intensity': intensity,
            'device': 'CPU',
            'output_path': str(output_path)
        }
    
    def process_video(self,
                      input_path: Union[str, Path],
                      output_path: Union[str, Path],
                      operation: str = 'resize',
                      **kwargs) -> dict:
 claude/setup-production-fullstack-NWyrz
        """Process video using GPU acceleration.

        """Process video using GPU acceleration (or CPU fallback).
 main

        Args:
            input_path: Path to input video.
            output_path: Path to save processed video.
            operation: Operation to perform ('resize', 'filter').
            **kwargs: Additional arguments for the operation.

        Returns:
            Dictionary containing processing metadata.
        """
        self._check_torch_available()

        input_path = Path(input_path)
        output_path = Path(output_path)

        # Open video
        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {input_path}")

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Get target size if resizing
        target_size = kwargs.get('size', (width, height))

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            target_size
        )

        processed_frames = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Use CPU fallback if PyTorch not available
            if not self._torch_available:
                if operation == 'resize':
                    processed_frame = cv2.resize(frame, target_size)
                else:
                    processed_frame = frame
            else:
                # Convert to tensor and move to GPU
                frame_tensor = torch.from_numpy(frame).to(self.device).permute(2, 0, 1)

                # Apply operation
                if operation == 'resize':
                    transform = transforms.Resize(target_size, antialias=True)
                    processed = transform(frame_tensor)
                else:
                    processed = frame_tensor

                # Convert back to numpy
                processed_frame = processed.permute(1, 2, 0).cpu().numpy().astype(np.uint8)

            # Write frame
            out.write(processed_frame)
            processed_frames += 1

        # Release resources
        cap.release()
        out.release()

        return {
            'original_size': (width, height),
            'new_size': target_size,
            'fps': fps,
            'total_frames': total_frames,
            'processed_frames': processed_frames,
            'device': 'CPU' if not self._torch_available else str(self.device),
            'output_path': str(output_path)
        }
    
    def get_device_info(self) -> dict:
        """Get information about the processing device.

        Returns:
            Dictionary containing device information.
        """
        base_info = {
            'device': self.device_type.upper(),
            'name': self.device_name,
            'backend': self.device_type
        }

        # Add PyTorch availability info
        if not self._torch_available:
            base_info['pytorch_available'] = False
            base_info['note'] = 'Install PyTorch for GPU support: pip install secure-media-processor[gpu]'
            return base_info

        base_info['pytorch_available'] = True

        if not self.gpu_enabled:
            return base_info

        # Add GPU-specific information based on type
        if self.device_type == 'cuda':
            base_info.update({
                'vendor': 'NVIDIA',
                'memory_total': torch.cuda.get_device_properties(0).total_memory / 1e9,
                'memory_allocated': torch.cuda.memory_allocated(0) / 1e9,
                'memory_cached': torch.cuda.memory_reserved(0) / 1e9,
                'cuda_version': torch.version.cuda
            })
        elif self.device_type == 'rocm':
            base_info.update({
                'vendor': 'AMD',
                'rocm_version': torch.version.hip if hasattr(torch.version, 'hip') else 'N/A'
            })
        elif self.device_type == 'mps':
            base_info.update({
                'vendor': 'Apple',
                'architecture': 'Apple Silicon (M1/M2/M3)'
            })
        elif self.device_type == 'xpu':
            base_info.update({
                'vendor': 'Intel',
                'architecture': 'Arc GPU'
            })

        return base_info
