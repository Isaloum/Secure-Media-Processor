"""Command-line interface for Secure Media Processor."""

import click
from pathlib import Path
from colorama import Fore, Style, init
import logging
from typing import Optional

from src.config import settings
from src.encryption import MediaEncryptor
from src.cloud_storage import CloudStorageManager
from src.gpu_processor import GPUMediaProcessor

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
    click.echo(f"{Fore.CYAN}📊 System Information{Style.RESET_ALL}\n")

    processor = GPUMediaProcessor()
    device_info = processor.get_device_info()

    click.echo(f"{Fore.YELLOW}Device:{Style.RESET_ALL} {device_info['device']}")
    click.echo(f"{Fore.YELLOW}Name:{Style.RESET_ALL} {device_info['name']}")

    # Check for GPU types (CUDA, ROCM, MPS, XPU) - not 'GPU'
    gpu_types = ['CUDA', 'ROCM', 'MPS', 'XPU']
    if device_info['device'] in gpu_types:
        # Show vendor if available
        if 'vendor' in device_info:
            click.echo(f"{Fore.YELLOW}Vendor:{Style.RESET_ALL} {device_info['vendor']}")

        # CUDA-specific info
        if device_info['device'] == 'CUDA':
            click.echo(f"{Fore.YELLOW}Total Memory:{Style.RESET_ALL} {device_info['memory_total']:.2f} GB")
            click.echo(f"{Fore.YELLOW}Allocated Memory:{Style.RESET_ALL} {device_info['memory_allocated']:.2f} GB")
            click.echo(f"{Fore.YELLOW}Cached Memory:{Style.RESET_ALL} {device_info['memory_cached']:.2f} GB")
            click.echo(f"{Fore.YELLOW}CUDA Version:{Style.RESET_ALL} {device_info['cuda_version']}")

        # ROCm-specific info
        elif device_info['device'] == 'ROCM':
            click.echo(f"{Fore.YELLOW}ROCm Version:{Style.RESET_ALL} {device_info.get('rocm_version', 'N/A')}")

        # Apple MPS-specific info
        elif device_info['device'] == 'MPS':
            click.echo(f"{Fore.YELLOW}Architecture:{Style.RESET_ALL} {device_info.get('architecture', 'Apple Silicon')}")

        # Intel XPU-specific info
        elif device_info['device'] == 'XPU':
            click.echo(f"{Fore.YELLOW}Architecture:{Style.RESET_ALL} {device_info.get('architecture', 'Intel Arc')}")

    # CPU mode - show note if PyTorch not available
    elif device_info['device'] == 'CPU':
        if not device_info.get('pytorch_available', True):
            click.echo(f"{Fore.YELLOW}Note:{Style.RESET_ALL} {device_info.get('note', 'GPU acceleration not available')}")


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


# =============================================================================
# Medical Imaging Commands
# =============================================================================

@cli.group()
def medical():
    """Medical imaging tools for DICOM processing and analysis."""
    pass


@medical.command('dicom-info')
@click.argument('path', type=click.Path(exists=True))
@click.option('--series', is_flag=True, help='List all series in directory')
def dicom_info(path: str, series: bool):
    """Display DICOM file or series information."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Reading DICOM data...{Style.RESET_ALL}\n")

    try:
        processor = DICOMProcessor()
        path_obj = Path(path)

        if series or path_obj.is_dir():
            # List all series
            series_list = processor.get_series_list(path)

            if not series_list:
                click.echo(f"{Fore.YELLOW}No DICOM series found in directory{Style.RESET_ALL}")
                return

            click.echo(f"{Fore.GREEN}Found {len(series_list)} series:{Style.RESET_ALL}\n")

            for i, s in enumerate(series_list, 1):
                click.echo(f"{Fore.YELLOW}Series {i}:{Style.RESET_ALL}")
                click.echo(f"  UID: {s['series_uid'][:50]}...")
                click.echo(f"  Modality: {s['modality']}")
                click.echo(f"  Description: {s['series_description'] or 'N/A'}")
                click.echo(f"  Patient ID: {s['patient_id']}")
                click.echo(f"  Study Date: {s['study_date']}")
                click.echo(f"  Slices: {s['num_slices']}")
                click.echo()
        else:
            # Single file info
            pixel_array, metadata = processor.read_dicom(path)

            click.echo(f"{Fore.GREEN}DICOM File Information{Style.RESET_ALL}\n")

            click.echo(f"{Fore.YELLOW}Patient:{Style.RESET_ALL}")
            click.echo(f"  ID: {metadata.patient_id or 'N/A'}")
            click.echo(f"  Name: {metadata.patient_name or 'N/A'}")
            click.echo(f"  Sex: {metadata.patient_sex or 'N/A'}")
            click.echo(f"  Age: {metadata.patient_age or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Study:{Style.RESET_ALL}")
            click.echo(f"  Date: {metadata.study_date or 'N/A'}")
            click.echo(f"  Description: {metadata.study_description or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Series:{Style.RESET_ALL}")
            click.echo(f"  Modality: {metadata.modality or 'N/A'}")
            click.echo(f"  Description: {metadata.series_description or 'N/A'}")

            click.echo(f"\n{Fore.YELLOW}Image:{Style.RESET_ALL}")
            click.echo(f"  Dimensions: {metadata.rows} x {metadata.columns}")
            click.echo(f"  Pixel Spacing: {metadata.pixel_spacing or 'N/A'}")
            click.echo(f"  Slice Thickness: {metadata.slice_thickness or 'N/A'}")

            if metadata.modality == 'MR':
                click.echo(f"\n{Fore.YELLOW}MRI Parameters:{Style.RESET_ALL}")
                click.echo(f"  Field Strength: {metadata.magnetic_field_strength or 'N/A'} T")
                click.echo(f"  Echo Time (TE): {metadata.echo_time or 'N/A'} ms")
                click.echo(f"  Repetition Time (TR): {metadata.repetition_time or 'N/A'} ms")
                click.echo(f"  Flip Angle: {metadata.flip_angle or 'N/A'} degrees")

    except Exception as e:
        click.echo(f"{Fore.RED}Error reading DICOM: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('anonymize')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--keep-uids', is_flag=True, help='Keep original study/series UIDs')
def anonymize_dicom(input_path: str, output_path: str, keep_uids: bool):
    """Anonymize DICOM file for HIPAA compliance."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Anonymizing DICOM file...{Style.RESET_ALL}")

    try:
        processor = DICOMProcessor()
        result = processor.anonymize_dicom(input_path, output_path, keep_study_uid=keep_uids)

        click.echo(f"{Fore.GREEN}File anonymized successfully!{Style.RESET_ALL}")
        click.echo(f"  Output: {result['output']}")
        click.echo(f"  New Patient ID: {result['new_patient_id']}")
        click.echo(f"  Fields removed: {len(result['removed_fields'])}")

        if result['removed_fields']:
            click.echo(f"\n{Fore.YELLOW}Removed/anonymized fields:{Style.RESET_ALL}")
            for field in result['removed_fields'][:10]:
                click.echo(f"    - {field}")
            if len(result['removed_fields']) > 10:
                click.echo(f"    ... and {len(result['removed_fields']) - 10} more")

    except Exception as e:
        click.echo(f"{Fore.RED}Anonymization failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('convert')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--format', 'output_format', type=click.Choice(['png', 'nifti']),
              default='png', help='Output format')
@click.option('--window-center', type=float, help='Window center for contrast')
@click.option('--window-width', type=float, help='Window width for contrast')
def convert_dicom(input_path: str, output_path: str, output_format: str,
                  window_center: Optional[float], window_width: Optional[float]):
    """Convert DICOM to PNG or NIfTI format."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available

    if not check_dicom_available():
        click.echo(f"{Fore.RED}DICOM support not available. Install with: pip install pydicom{Style.RESET_ALL}")
        raise click.Abort()

    click.echo(f"{Fore.CYAN}Converting DICOM to {output_format.upper()}...{Style.RESET_ALL}")

    try:
        processor = DICOMProcessor()

        if output_format == 'png':
            result = processor.convert_to_png(
                input_path, output_path,
                window_center=window_center,
                window_width=window_width
            )
            click.echo(f"{Fore.GREEN}Converted to PNG successfully!{Style.RESET_ALL}")
            click.echo(f"  Output: {result['output']}")
            click.echo(f"  Size: {result['size']}")
            click.echo(f"  Modality: {result['modality']}")

        elif output_format == 'nifti':
            result = processor.convert_to_nifti(input_path, output_path)
            click.echo(f"{Fore.GREEN}Converted to NIfTI successfully!{Style.RESET_ALL}")
            click.echo(f"  Output: {result['output']}")
            click.echo(f"  Volume shape: {result['volume_shape']}")
            click.echo(f"  Voxel spacing: {result['voxel_spacing']}")
            click.echo(f"  Slices: {result['num_slices']}")

    except Exception as e:
        click.echo(f"{Fore.RED}Conversion failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('preprocess')
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--bias-correction/--no-bias-correction', default=True,
              help='Apply N4 bias field correction')
@click.option('--denoise/--no-denoise', default=True, help='Apply noise reduction')
@click.option('--normalize', type=click.Choice(['zscore', 'minmax', 'percentile']),
              default='zscore', help='Normalization method')
@click.option('--enhance-contrast', is_flag=True, help='Apply CLAHE contrast enhancement')
def preprocess_medical(input_path: str, output_path: str, bias_correction: bool,
                       denoise: bool, normalize: str, enhance_contrast: bool):
    """Preprocess medical image for ML analysis."""
    from src.dicom_processor import DICOMProcessor, check_dicom_available
    from src.medical_preprocessing import (
        MedicalImagePreprocessor, PreprocessingConfig, NormalizationMethod
    )
    import numpy as np

    click.echo(f"{Fore.CYAN}Preprocessing medical image...{Style.RESET_ALL}")

    try:
        # Load image (DICOM or standard format)
        input_path_obj = Path(input_path)

        if input_path_obj.suffix.lower() in ['.dcm', '.dicom'] or input_path_obj.is_dir():
            if not check_dicom_available():
                click.echo(f"{Fore.RED}DICOM support not available{Style.RESET_ALL}")
                raise click.Abort()

            processor = DICOMProcessor()
            if input_path_obj.is_dir():
                volume = processor.read_dicom_series(input_path)
                image = volume.pixel_data
            else:
                image, _ = processor.read_dicom(input_path)
        else:
            from PIL import Image
            img = Image.open(input_path).convert('L')
            image = np.array(img, dtype=np.float32)

        # Configure preprocessing
        norm_method = {
            'zscore': NormalizationMethod.ZSCORE,
            'minmax': NormalizationMethod.MINMAX,
            'percentile': NormalizationMethod.PERCENTILE
        }[normalize]

        config = PreprocessingConfig(
            normalize=True,
            normalization_method=norm_method,
            denoise=denoise,
            bias_correction=bias_correction,
            enhance_contrast=enhance_contrast
        )

        # Run preprocessing
        preprocessor = MedicalImagePreprocessor(config)
        result = preprocessor.preprocess(image)

        # Save result
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if output_path_obj.suffix.lower() == '.npy':
            np.save(output_path, result.data)
        else:
            from PIL import Image
            # Normalize to 0-255 for saving as image
            img_data = result.data
            if img_data.ndim == 3:
                img_data = img_data[img_data.shape[0] // 2]  # Middle slice
            img_data = ((img_data - img_data.min()) / (img_data.max() - img_data.min() + 1e-8) * 255).astype(np.uint8)
            Image.fromarray(img_data).save(output_path)

        click.echo(f"{Fore.GREEN}Preprocessing complete!{Style.RESET_ALL}")
        click.echo(f"  Output: {output_path}")
        click.echo(f"  Original shape: {result.original_shape}")
        click.echo(f"  Final shape: {result.final_shape}")
        click.echo(f"\n{Fore.YELLOW}Steps applied:{Style.RESET_ALL}")
        for step in result.steps_applied:
            click.echo(f"    - {step}")

    except Exception as e:
        click.echo(f"{Fore.RED}Preprocessing failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('predict')
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--model', type=click.Path(exists=True), required=True,
              help='Path to trained model (.pt, .pth, or .onnx)')
@click.option('--model-type', type=click.Choice(['pytorch', 'onnx', 'torchscript']),
              default='pytorch', help='Model type')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU for inference')
@click.option('--generate-heatmap', is_flag=True, help='Generate attention heatmap')
@click.option('--output-report', type=click.Path(), help='Save report to file')
def predict_cancer(input_path: str, model: str, model_type: str, gpu: bool,
                   generate_heatmap: bool, output_report: Optional[str]):
    """Run cancer prediction on MRI image/volume."""
    from src.ml_inference import (
        CancerPredictionPipeline, ModelConfig, ModelType, PredictionType, check_ml_available
    )

    # Check ML availability
    ml_status = check_ml_available()
    if model_type in ['pytorch', 'torchscript'] and not ml_status['pytorch']:
        click.echo(f"{Fore.RED}PyTorch not available. Install with: pip install torch{Style.RESET_ALL}")
        raise click.Abort()
    if model_type == 'onnx' and not ml_status['onnx']:
        click.echo(f"{Fore.RED}ONNX Runtime not available. Install with: pip install onnxruntime{Style.RESET_ALL}")
        raise click.Abort()

    if gpu and not ml_status['gpu']:
        click.echo(f"{Fore.YELLOW}GPU not available, using CPU{Style.RESET_ALL}")
        gpu = False

    click.echo(f"{Fore.CYAN}Running cancer prediction...{Style.RESET_ALL}\n")

    try:
        # Configure model
        type_map = {
            'pytorch': ModelType.PYTORCH,
            'onnx': ModelType.ONNX,
            'torchscript': ModelType.TORCHSCRIPT
        }

        config = ModelConfig(
            model_path=model,
            model_type=type_map[model_type],
            prediction_type=PredictionType.BINARY,
            use_gpu=gpu,
            class_names=["No Cancer", "Cancer"]
        )

        # Create pipeline
        pipeline = CancerPredictionPipeline(config, use_preprocessing=True)

        # Check if DICOM
        input_path_obj = Path(input_path)
        if input_path_obj.suffix.lower() in ['.dcm', '.dicom'] or input_path_obj.is_dir():
            result = pipeline.predict_from_dicom(input_path, generate_report=True)
        else:
            # Load as numpy/image
            import numpy as np
            from PIL import Image
            img = Image.open(input_path).convert('L')
            image = np.array(img, dtype=np.float32)
            result = pipeline.predict_single(image, generate_heatmap=generate_heatmap)

        # Display results
        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}PREDICTION RESULTS{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}{'=' * 50}{Style.RESET_ALL}\n")

        if 'final_probability' in result:
            prob = result['final_probability']
            label = result['predicted_label']
            conf = result.get('confidence', prob if prob > 0.5 else 1 - prob)

            color = Fore.RED if label == 'Cancer' else Fore.GREEN
            click.echo(f"{Fore.YELLOW}Prediction:{Style.RESET_ALL} {color}{label}{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Cancer Probability:{Style.RESET_ALL} {prob * 100:.1f}%")
            click.echo(f"{Fore.YELLOW}Confidence:{Style.RESET_ALL} {conf * 100:.1f}%")

            if 'most_suspicious_slice' in result:
                click.echo(f"{Fore.YELLOW}Most Suspicious Slice:{Style.RESET_ALL} #{result['most_suspicious_slice'] + 1}")
                click.echo(f"{Fore.YELLOW}Total Slices:{Style.RESET_ALL} {result['num_slices']}")
        else:
            pred = result.get('prediction', {})
            click.echo(f"{Fore.YELLOW}Prediction:{Style.RESET_ALL} {pred.get('predicted_label', 'N/A')}")
            click.echo(f"{Fore.YELLOW}Confidence:{Style.RESET_ALL} {pred.get('confidence', 0) * 100:.1f}%")

        # Save report if requested
        if output_report and 'report' in result:
            Path(output_report).write_text(result['report'])
            click.echo(f"\n{Fore.GREEN}Report saved to: {output_report}{Style.RESET_ALL}")

        # Print full report to console
        if 'report' in result:
            click.echo(f"\n{result['report']}")

    except Exception as e:
        click.echo(f"{Fore.RED}Prediction failed: {e}{Style.RESET_ALL}")
        raise click.Abort()


@medical.command('info')
def medical_info():
    """Display medical imaging capabilities and dependencies."""
    from src.dicom_processor import check_dicom_available
    from src.ml_inference import check_ml_available

    click.echo(f"{Fore.CYAN}Medical Imaging Capabilities{Style.RESET_ALL}\n")

    # DICOM support
    dicom_available = check_dicom_available()
    status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if dicom_available else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"{Fore.YELLOW}DICOM Support:{Style.RESET_ALL} {status}")
    if not dicom_available:
        click.echo(f"  Install with: pip install pydicom")

    # ML support
    ml_status = check_ml_available()
    click.echo(f"\n{Fore.YELLOW}ML Inference:{Style.RESET_ALL}")

    pytorch_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['pytorch'] else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"  PyTorch: {pytorch_status}")

    onnx_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['onnx'] else f"{Fore.RED}Not installed{Style.RESET_ALL}"
    click.echo(f"  ONNX Runtime: {onnx_status}")

    gpu_status = f"{Fore.GREEN}Available{Style.RESET_ALL}" if ml_status['gpu'] else f"{Fore.YELLOW}CPU only{Style.RESET_ALL}"
    click.echo(f"  GPU Acceleration: {gpu_status}")

    # Preprocessing dependencies
    click.echo(f"\n{Fore.YELLOW}Preprocessing:{Style.RESET_ALL}")

    try:
        import scipy
        click.echo(f"  scipy: {Fore.GREEN}Available{Style.RESET_ALL}")
    except ImportError:
        click.echo(f"  scipy: {Fore.RED}Not installed{Style.RESET_ALL}")

    try:
        import skimage
        click.echo(f"  scikit-image: {Fore.GREEN}Available{Style.RESET_ALL}")
    except ImportError:
        click.echo(f"  scikit-image: {Fore.RED}Not installed{Style.RESET_ALL}")

    click.echo(f"\n{Fore.CYAN}Install all medical dependencies:{Style.RESET_ALL}")
    click.echo(f"  pip install pydicom nibabel scipy scikit-image")


if __name__ == '__main__':
    cli()
