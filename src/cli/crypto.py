"""Encryption and decryption CLI commands."""

import click
from colorama import Fore, Style
from typing import Optional

from src.config import settings
from src.encryption import MediaEncryptor


@click.command()
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


@click.command()
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
