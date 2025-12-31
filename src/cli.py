"""Command-line interface for Secure Media Processor."""

import click
from pathlib import Path
from colorama import Fore, Style, init
import logging
from typing import Optional

from src.config import settings
from src.encryption import MediaEncryptor
from src.cloud_storage import CloudStorageManager

# Make GPU processor optional for macOS compatibility
try:
    from src.gpu_processor import GPUMediaProcessor
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    GPUMediaProcessor = None

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Secure Media Processor - Privacy-focused media processing with GPU acceleration."""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--key-path', type=click.Path(), help='Path to encryption key')
def encrypt(input_file: str, output_file: str, key_path: Optional[str]):
    """Encrypt a media file."""
    click.echo(f"{Fore.CYAN}🔒 Encrypting file...{Style.RESET_ALL}")
    
    try:
        key_path = key_path or settings.master_key_path
        encryptor = MediaEncryptor(key_path)
        
        result = encryptor.encrypt_file(input_file, output_file)
        
        click.echo(f"{Fore.GREEN}✓ File encrypted successfully!{Style.RESET_ALL}")
        click.echo(f"  Original size: {result['original_size']:,} bytes")
        click.echo(f"  Encrypted size: {result['encrypted_size']:,} bytes")
        click.echo(f"  Algorithm: {result['algorithm']}")
        click.echo(f"  Output: {output_file}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Encryption failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--key-path', type=click.Path(), help='Path to encryption key')
def decrypt(input_file: str, output_file: str, key_path: Optional[str]):
    """Decrypt a media file."""
    click.echo(f"{Fore.CYAN}🔓 Decrypting file...{Style.RESET_ALL}")
    
    try:
        key_path = key_path or settings.master_key_path
        encryptor = MediaEncryptor(key_path)
        
        result = encryptor.decrypt_file(input_file, output_file)
        
        click.echo(f"{Fore.GREEN}✓ File decrypted successfully!{Style.RESET_ALL}")
        click.echo(f"  Encrypted size: {result['encrypted_size']:,} bytes")
        click.echo(f"  Decrypted size: {result['decrypted_size']:,} bytes")
        click.echo(f"  Output: {output_file}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Decryption failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
@click.argument('local_file', type=click.Path(exists=True))
@click.option('--remote-key', help='Remote object key')
@click.option('--bucket', help='S3 bucket name')
def upload(local_file: str, remote_key: Optional[str], bucket: Optional[str]):
    """Upload an encrypted file to cloud storage."""
    click.echo(f"{Fore.CYAN}☁️  Uploading to cloud storage...{Style.RESET_ALL}")
    
    try:
        bucket_name = bucket or settings.aws_bucket_name
        if not bucket_name:
            raise ValueError("Bucket name not specified")
        
        storage = CloudStorageManager(
            bucket_name=bucket_name,
            region=settings.aws_region,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key
        )
        
        result = storage.upload_file(local_file, remote_key=remote_key)
        
        if result['success']:
            click.echo(f"{Fore.GREEN}✓ File uploaded successfully!{Style.RESET_ALL}")
            click.echo(f"  Remote key: {result['remote_key']}")
            click.echo(f"  Size: {result['size']:,} bytes")
            click.echo(f"  Checksum: {result['checksum']}")
        else:
            click.echo(f"{Fore.RED}✗ Upload failed: {result['error']}{Style.RESET_ALL}")
            raise click.Abort()
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Upload failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
@click.argument('remote_key')
@click.argument('local_file', type=click.Path())
@click.option('--bucket', help='S3 bucket name')
@click.option('--verify/--no-verify', default=True, help='Verify checksum')
def download(remote_key: str, local_file: str, bucket: Optional[str], verify: bool):
    """Download an encrypted file from cloud storage."""
    click.echo(f"{Fore.CYAN}☁️  Downloading from cloud storage...{Style.RESET_ALL}")
    
    try:
        bucket_name = bucket or settings.aws_bucket_name
        if not bucket_name:
            raise ValueError("Bucket name not specified")
        
        storage = CloudStorageManager(
            bucket_name=bucket_name,
            region=settings.aws_region,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key
        )
        
        result = storage.download_file(remote_key, local_file, verify_checksum=verify)
        
        if result['success']:
            click.echo(f"{Fore.GREEN}✓ File downloaded successfully!{Style.RESET_ALL}")
            click.echo(f"  Local path: {result['local_path']}")
            click.echo(f"  Size: {result['size']:,} bytes")
            click.echo(f"  Checksum verified: {result['checksum_verified']}")
        else:
            click.echo(f"{Fore.RED}✗ Download failed: {result['error']}{Style.RESET_ALL}")
            raise click.Abort()
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Download failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--width', type=int, required=True, help='Target width')
@click.option('--height', type=int, required=True, help='Target height')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU acceleration')
def resize(input_file: str, output_file: str, width: int, height: int, gpu: bool):
    """Resize an image using GPU acceleration."""
    if not GPU_AVAILABLE:
        click.echo(f"{Fore.YELLOW}⚠️  GPU processing not available (PyTorch not installed){Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Install PyTorch to enable GPU features: pip install torch torchvision{Style.RESET_ALL}")
        raise click.Abort()
    
    click.echo(f"{Fore.CYAN}🖼️  Resizing image...{Style.RESET_ALL}")
    
    try:
        processor = GPUMediaProcessor(gpu_enabled=gpu)
        
        result = processor.resize_image(
            input_file,
            output_file,
            size=(width, height)
        )
        
        click.echo(f"{Fore.GREEN}✓ Image resized successfully!{Style.RESET_ALL}")
        click.echo(f"  Original size: {result['original_size']}")
        click.echo(f"  New size: {result['new_size']}")
        click.echo(f"  Device: {result['device']}")
        click.echo(f"  Output: {result['output_path']}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Resize failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--filter', type=click.Choice(['blur', 'sharpen', 'edge']), 
              default='blur', help='Filter type')
@click.option('--intensity', type=float, default=1.0, help='Filter intensity')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU acceleration')
def filter_image(input_file: str, output_file: str, filter: str, intensity: float, gpu: bool):
    """Apply filters to an image."""
    if not GPU_AVAILABLE:
        click.echo(f"{Fore.YELLOW}⚠️  GPU processing not available (PyTorch not installed){Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Install PyTorch to enable GPU features: pip install torch torchvision{Style.RESET_ALL}")
        raise click.Abort()
    
    click.echo(f"{Fore.CYAN}🎨 Applying filter...{Style.RESET_ALL}")
    
    try:
        processor = GPUMediaProcessor(gpu_enabled=gpu)
        
        result = processor.apply_filter(
            input_file,
            output_file,
            filter_type=filter,
            intensity=intensity
        )
        
        click.echo(f"{Fore.GREEN}✓ Filter applied successfully!{Style.RESET_ALL}")
        click.echo(f"  Filter: {result['filter_type']}")
        click.echo(f"  Intensity: {result['intensity']}")
        click.echo(f"  Device: {result['device']}")
        click.echo(f"  Output: {result['output_path']}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Filter failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@cli.command()
def info():
    """Display system and GPU information."""
    click.echo(f"{Fore.CYAN}📊 System Information{Style.RESET_ALL}\n")
    
    if not GPU_AVAILABLE:
        click.echo(f"{Fore.YELLOW}GPU Processing:{Style.RESET_ALL} Not available (PyTorch not installed)")
        click.echo(f"{Fore.YELLOW}Device:{Style.RESET_ALL} CPU only")
        click.echo(f"\n{Fore.CYAN}To enable GPU features:{Style.RESET_ALL}")
        click.echo(f"  pip install torch torchvision")
        return
    
    processor = GPUMediaProcessor()
    device_info = processor.get_device_info()
    
    click.echo(f"{Fore.YELLOW}Device:{Style.RESET_ALL} {device_info['device']}")
    click.echo(f"{Fore.YELLOW}Name:{Style.RESET_ALL} {device_info['name']}")
    
    if device_info['device'] == 'GPU':
        click.echo(f"{Fore.YELLOW}Total Memory:{Style.RESET_ALL} {device_info['memory_total']:.2f} GB")
        click.echo(f"{Fore.YELLOW}Allocated Memory:{Style.RESET_ALL} {device_info['memory_allocated']:.2f} GB")
        click.echo(f"{Fore.YELLOW}Cached Memory:{Style.RESET_ALL} {device_info['memory_cached']:.2f} GB")
        click.echo(f"{Fore.YELLOW}CUDA Version:{Style.RESET_ALL} {device_info['cuda_version']}")


if __name__ == '__main__':
    cli()
