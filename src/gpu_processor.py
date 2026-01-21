"""GPU-accelerated media processing module."""

import torch
import torchvision.transforms as transforms
from torchvision.io import read_image, write_jpeg, write_png
import cv2
import numpy as np
from pathlib import Path
from typing import Union, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class GPUMediaProcessor:
    """Handle GPU-accelerated media processing operations."""
    
    def __init__(self, gpu_enabled: bool = True, device_id: int = 0):
        """Initialize GPU processor.
        
        Args:
            gpu_enabled: Whether to use GPU acceleration.
            device_id: CUDA device ID to use.
        """
        self.gpu_enabled = gpu_enabled and torch.cuda.is_available()
        
        if self.gpu_enabled:
            self.device = torch.device(f'cuda:{device_id}')
            logger.info(f"GPU enabled: {torch.cuda.get_device_name(device_id)}")
            logger.info(f"GPU memory: {torch.cuda.get_device_properties(device_id).total_memory / 1e9:.2f} GB")
        else:
            self.device = torch.device('cpu')
            logger.info("GPU not available, using CPU")
    
    def resize_image(self,
                     input_path: Union[str, Path],
                     output_path: Union[str, Path],
                     size: Tuple[int, int],
                     maintain_aspect_ratio: bool = True) -> dict:
        """Resize an image using GPU acceleration.
        
        Args:
            input_path: Path to input image.
            output_path: Path to save resized image.
            size: Target size (width, height).
            maintain_aspect_ratio: Whether to maintain aspect ratio.
            
        Returns:
            Dictionary containing processing metadata.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
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
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
        if self.gpu_enabled:
            torch.cuda.empty_cache()

        return result
    
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
        if self.gpu_enabled:
            torch.cuda.empty_cache()
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
        """Apply filters to an image using GPU.
        
        Args:
            input_path: Path to input image.
            output_path: Path to save filtered image.
            filter_type: Type of filter ('blur', 'sharpen', 'edge', 'denoise').
            intensity: Filter intensity (0.0 to 2.0).
            
        Returns:
            Dictionary containing processing metadata.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def process_video(self,
                      input_path: Union[str, Path],
                      output_path: Union[str, Path],
                      operation: str = 'resize',
                      **kwargs) -> dict:
        """Process video using GPU acceleration.
        
        Args:
            input_path: Path to input video.
            output_path: Path to save processed video.
            operation: Operation to perform ('resize', 'filter').
            **kwargs: Additional arguments for the operation.
            
        Returns:
            Dictionary containing processing metadata.
        """
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
            'device': str(self.device),
            'output_path': str(output_path)
        }
    
    def get_device_info(self) -> dict:
        """Get information about the processing device.
        
        Returns:
            Dictionary containing device information.
        """
        if self.gpu_enabled:
            return {
                'device': 'GPU',
                'name': torch.cuda.get_device_name(0),
                'memory_total': torch.cuda.get_device_properties(0).total_memory / 1e9,
                'memory_allocated': torch.cuda.memory_allocated(0) / 1e9,
                'memory_cached': torch.cuda.memory_reserved(0) / 1e9,
                'cuda_version': torch.version.cuda
            }
        else:
            return {
                'device': 'CPU',
                'name': 'CPU Processing'
            }
