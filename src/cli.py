"""Command-line interface for Secure Media Processor."""

import click
from pathlib import Path
from colorama import Fore, Style, init
import logging
from typing import Optional

from src.config import settings
from src.encryption import MediaEncryptor
from src.cloud_storage import CloudStorageManager

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0')
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
    from src.license_manager import get_license_manager, FeatureFlags

    # Check license for cloud storage feature
    manager = get_license_manager()
    if not manager.check_feature(FeatureFlags.CLOUD_STORAGE):
        click.echo(f"{Fore.RED}✗ Cloud storage requires a Pro or Enterprise license{Style.RESET_ALL}")
        click.echo(f"\n{Fore.CYAN}💎 Upgrade to unlock:{Style.RESET_ALL}")
        click.echo(f"  • AWS S3, Google Drive, Dropbox connectors")
        click.echo(f"  • GPU-accelerated processing")
        click.echo(f"  • Batch operations")
        click.echo(f"\n{Fore.GREEN}Visit https://secure-media-processor.com/pricing{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Or activate your license: smp license activate YOUR-LICENSE-KEY{Style.RESET_ALL}")
        raise click.Abort()

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
    from src.license_manager import get_license_manager, FeatureFlags

    # Check license for cloud storage feature
    manager = get_license_manager()
    if not manager.check_feature(FeatureFlags.CLOUD_STORAGE):
        click.echo(f"{Fore.RED}✗ Cloud storage requires a Pro or Enterprise license{Style.RESET_ALL}")
        click.echo(f"\n{Fore.YELLOW}Activate your license: smp license activate YOUR-LICENSE-KEY{Style.RESET_ALL}")
        raise click.Abort()

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
    from src.license_manager import get_license_manager, FeatureFlags
    from src.gpu_processor import GPUMediaProcessor

    # Check license for GPU processing if requested
    if gpu:
        manager = get_license_manager()
        if not manager.check_feature(FeatureFlags.GPU_PROCESSING):
            click.echo(f"{Fore.RED}✗ GPU processing requires a Pro or Enterprise license{Style.RESET_ALL}")
            click.echo(f"\n{Fore.YELLOW}Activate your license: smp license activate YOUR-LICENSE-KEY{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Or use CPU: add --no-gpu flag{Style.RESET_ALL}")
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
    from src.license_manager import get_license_manager, FeatureFlags
    from src.gpu_processor import GPUMediaProcessor

    # Check license for GPU processing if requested
    if gpu:
        manager = get_license_manager()
        if not manager.check_feature(FeatureFlags.GPU_PROCESSING):
            click.echo(f"{Fore.RED}✗ GPU processing requires a Pro or Enterprise license{Style.RESET_ALL}")
            click.echo(f"\n{Fore.YELLOW}Activate your license: smp license activate YOUR-LICENSE-KEY{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Or use CPU: add --no-gpu flag{Style.RESET_ALL}")
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
    from src.gpu_processor import GPUMediaProcessor

    click.echo(f"{Fore.CYAN}📊 System Information{Style.RESET_ALL}\n")

    processor = GPUMediaProcessor()
    device_info = processor.get_device_info()
    
    click.echo(f"{Fore.YELLOW}Device:{Style.RESET_ALL} {device_info['device']}")
    click.echo(f"{Fore.YELLOW}Name:{Style.RESET_ALL} {device_info['name']}")
    
    if device_info['device'] == 'GPU':
        click.echo(f"{Fore.YELLOW}Total Memory:{Style.RESET_ALL} {device_info['memory_total']:.2f} GB")
        click.echo(f"{Fore.YELLOW}Allocated Memory:{Style.RESET_ALL} {device_info['memory_allocated']:.2f} GB")
        click.echo(f"{Fore.YELLOW}Cached Memory:{Style.RESET_ALL} {device_info['memory_cached']:.2f} GB")
        click.echo(f"{Fore.YELLOW}CUDA Version:{Style.RESET_ALL} {device_info['cuda_version']}")


@cli.group()
def license():
    """Manage license and premium features."""
    pass


@license.command()
@click.argument('license_key')
@click.option('--email', prompt=True, help='Your email address')
def activate(license_key: str, email: str):
    """Activate a license key."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}🔑 Activating license...{Style.RESET_ALL}")

    try:
        manager = get_license_manager()
        license_obj = manager.activate_license(license_key, email)

        click.echo(f"{Fore.GREEN}✓ License activated successfully!{Style.RESET_ALL}\n")
        click.echo(f"{Fore.YELLOW}License Type:{Style.RESET_ALL} {license_obj.license_type.value.upper()}")
        click.echo(f"{Fore.YELLOW}Email:{Style.RESET_ALL} {license_obj.email}")

        if license_obj.expires_at:
            days_left = (license_obj.expires_at - license_obj.issued_at).days
            click.echo(f"{Fore.YELLOW}Valid For:{Style.RESET_ALL} {days_left} days")
        else:
            click.echo(f"{Fore.YELLOW}Valid For:{Style.RESET_ALL} Lifetime")

        click.echo(f"\n{Fore.GREEN}Enabled Features:{Style.RESET_ALL}")
        if license_obj.features:
            for feature in license_obj.features:
                click.echo(f"  ✓ {feature.replace('_', ' ').title()}")
        else:
            click.echo(f"  {Fore.YELLOW}(Free tier - local encryption only){Style.RESET_ALL}")

        click.echo(f"\n{Fore.CYAN}🎉 Thank you for supporting Secure Media Processor!{Style.RESET_ALL}")

    except ValueError as e:
        click.echo(f"{Fore.RED}✗ Activation failed: {e}{Style.RESET_ALL}")
        click.echo(f"\n{Fore.YELLOW}Need help? Visit https://secure-media-processor.com/support{Style.RESET_ALL}")
        raise click.Abort()
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
        raise click.Abort()


@license.command()
def status():
    """Show current license status."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}📋 License Status{Style.RESET_ALL}\n")

    try:
        manager = get_license_manager()
        info = manager.get_license_info()

        if info['active']:
            click.echo(f"{Fore.GREEN}Status:{Style.RESET_ALL} ✓ Active")
            click.echo(f"{Fore.YELLOW}Type:{Style.RESET_ALL} {info['type'].upper()}")
            click.echo(f"{Fore.YELLOW}Email:{Style.RESET_ALL} {info['email']}")

            if info['days_remaining']:
                color = Fore.RED if info['days_remaining'] < 30 else Fore.GREEN
                click.echo(f"{Fore.YELLOW}Expires:{Style.RESET_ALL} {color}{info['days_remaining']} days{Style.RESET_ALL}")
            else:
                click.echo(f"{Fore.YELLOW}Expires:{Style.RESET_ALL} {Fore.GREEN}Never (Lifetime){Style.RESET_ALL}")

            click.echo(f"{Fore.YELLOW}Devices:{Style.RESET_ALL} {info['activated_devices']}/{info['max_devices']}")

            click.echo(f"\n{Fore.GREEN}Enabled Features:{Style.RESET_ALL}")
            if info['features']:
                for feature in info['features']:
                    click.echo(f"  ✓ {feature.replace('_', ' ').title()}")
            else:
                click.echo(f"  {Fore.YELLOW}(None - Free tier){Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}Status:{Style.RESET_ALL} Free Tier")
            click.echo(f"{Fore.YELLOW}Message:{Style.RESET_ALL} {info['message']}")
            click.echo(f"\n{Fore.CYAN}💎 Upgrade to Pro or Enterprise for premium features:{Style.RESET_ALL}")
            click.echo(f"  • Cloud storage (S3, Drive, Dropbox)")
            click.echo(f"  • GPU-accelerated processing")
            click.echo(f"  • Batch operations")
            click.echo(f"  • Multi-cloud sync (Enterprise)")
            click.echo(f"  • Priority support (Enterprise)")
            click.echo(f"\n{Fore.GREEN}Visit https://secure-media-processor.com/pricing{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        raise click.Abort()


@license.command()
@click.confirmation_option(prompt='Are you sure you want to deactivate your license?')
def deactivate():
    """Deactivate license on this device."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}🔓 Deactivating license...{Style.RESET_ALL}")

    try:
        manager = get_license_manager()
        if manager.deactivate_license():
            click.echo(f"{Fore.GREEN}✓ License deactivated successfully{Style.RESET_ALL}")
            click.echo(f"\n{Fore.YELLOW}You can now activate this license on another device.{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Free tier features remain available.{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}No active license found{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        raise click.Abort()


if __name__ == '__main__':
    cli()
