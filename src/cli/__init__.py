"""CLI package for Secure Media Processor.

This package provides the command-line interface:
- main: Entry point and all CLI commands

Commands are organized by function:
- Encryption: encrypt, decrypt
- Cloud: upload, download
- Media: resize, filter, info
- License: activate, status, deactivate
- Medical: dicom-info, anonymize, convert, preprocess, predict, segment

Example:
    $ smp encrypt input.jpg output.enc
    $ smp upload file.enc --bucket my-bucket
    $ smp medical predict scan.dcm --model model.pt
"""

from .main import cli

__all__ = ['cli']
