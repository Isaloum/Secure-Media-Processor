"""Media processing CLI commands."""

import click
from colorama import Fore, Style

from src.gpu_processor import GPUMediaProcessor


@click.command()
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


@click.command('filter')
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--filter', 'filter_type', type=click.Choice(['blur', 'sharpen', 'edge']),
              default='blur', help='Filter type')
@click.option('--intensity', type=float, default=1.0, help='Filter intensity')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU acceleration')
def filter_image(input_file: str, output_file: str, filter_type: str, intensity: float, gpu: bool):
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
            filter_type=filter_type,
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


@click.command()
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
