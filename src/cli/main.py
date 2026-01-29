"""Command-line interface for Secure Media Processor.

This is the main entry point that assembles all CLI commands from
modular subcommand files.
"""

import click
from colorama import init
import logging

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.1')
def cli():
    """Secure Media Processor - Privacy-focused media processing with GPU acceleration."""
    pass


# Import and register commands from submodules
from src.cli.crypto import encrypt, decrypt
from src.cli.cloud import upload, download
from src.cli.media import resize, filter_image, info
from src.cli.license import license
from src.cli.medical import medical

# Register individual commands
cli.add_command(encrypt)
cli.add_command(decrypt)
cli.add_command(upload)
cli.add_command(download)
cli.add_command(resize)
cli.add_command(filter_image, name='filter')
cli.add_command(info)

# Register command groups
cli.add_command(license)
cli.add_command(medical)


if __name__ == '__main__':
    cli()
