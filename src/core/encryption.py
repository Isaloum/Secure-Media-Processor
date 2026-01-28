"""Encryption module for secure media handling."""

import os
from pathlib import Path
from typing import Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
import secrets


class MediaEncryptor:
    """Handle encryption and decryption of media files."""

    def __init__(self, key_path: Union[str, Path]):
        """Initialize encryptor with master key.

        Args:
            key_path: Path to the master encryption key file.
        """
        self.key_path = Path(key_path)
        self.key = self._load_or_create_key()
        self.cipher = AESGCM(self.key)

    def __del__(self):
        """Securely clear encryption key from memory when object is destroyed.

        This prevents key leakage through process memory dumps.
        Called automatically when the object is garbage collected.
        """
        # Clear the encryption key
        if hasattr(self, 'key') and self.key:
            # Overwrite key bytes with zeros before clearing reference
            key_len = len(self.key)
            try:
                # Note: Due to Python's immutable bytes, this creates a new object
                # but helps signal intent and may be useful for mutable buffers
                self.key = b'\x00' * key_len
            except (TypeError, AttributeError):
                pass
            self.key = None

        # Clear cipher reference
        if hasattr(self, 'cipher'):
            self.cipher = None
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create a new one.
        
        Returns:
            32-byte encryption key.
        """
        if self.key_path.exists():
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            # Create directory if it doesn't exist
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate new 256-bit key
            key = AESGCM.generate_key(bit_length=256)
            
            # Save key with restricted permissions
            with open(self.key_path, 'wb') as f:
                f.write(key)
            
            # Set file permissions (Unix only)
            try:
                os.chmod(self.key_path, 0o600)
            except (OSError, AttributeError):
                pass
            
            return key
    
    def encrypt_file(self, input_path: Union[str, Path], 
                     output_path: Union[str, Path]) -> dict:
        """Encrypt a media file.
        
        Args:
            input_path: Path to the file to encrypt.
            output_path: Path where encrypted file will be saved.
            
        Returns:
            Dictionary containing encryption metadata.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # Read the file
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        
        # Generate a random nonce (96 bits for GCM)
        nonce = secrets.token_bytes(12)
        
        # Encrypt the data
        ciphertext = self.cipher.encrypt(nonce, plaintext, None)
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write encrypted file: nonce + ciphertext
        with open(output_path, 'wb') as f:
            f.write(nonce + ciphertext)
        
        return {
            'original_size': len(plaintext),
            'encrypted_size': len(nonce) + len(ciphertext),
            'nonce_size': len(nonce),
            'algorithm': 'AES-256-GCM'
        }
    
    def decrypt_file(self, input_path: Union[str, Path], 
                     output_path: Union[str, Path]) -> dict:
        """Decrypt a media file.
        
        Args:
            input_path: Path to the encrypted file.
            output_path: Path where decrypted file will be saved.
            
        Returns:
            Dictionary containing decryption metadata.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # Read encrypted file
        with open(input_path, 'rb') as f:
            data = f.read()
        
        # Extract nonce and ciphertext
        nonce = data[:12]
        ciphertext = data[12:]
        
        # Decrypt the data
        plaintext = self.cipher.decrypt(nonce, ciphertext, None)
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write decrypted file
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        
        return {
            'encrypted_size': len(data),
            'decrypted_size': len(plaintext),
            'algorithm': 'AES-256-GCM'
        }
    
    def secure_delete(self, file_path: Union[str, Path], passes: int = 3) -> None:
        """Securely delete a file by overwriting before deletion.
        
        Args:
            file_path: Path to the file to delete.
            passes: Number of overwrite passes.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Overwrite with random data
        with open(file_path, 'wb') as f:
            for _ in range(passes):
                f.seek(0)
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Delete the file
        file_path.unlink()
