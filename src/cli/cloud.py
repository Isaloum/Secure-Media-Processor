"""Cloud storage CLI commands."""

import click
from colorama import Fore, Style
from typing import Optional

from src.config import settings
from src.cloud_storage import CloudStorageManager


@click.command()
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


@click.command()
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
