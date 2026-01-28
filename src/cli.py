"""Command-line interface for Secure Media Processor.

This module is maintained for backward compatibility.
New code should import from src.cli instead.
"""

# Re-export from new location for backward compatibility
from src.cli.main import cli

__all__ = ['cli']

# Allow running as main module
if __name__ == '__main__':
    cli()
