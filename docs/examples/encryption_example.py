#!/usr/bin/env python3
"""Example: File encryption and decryption with Secure Media Processor.

This example demonstrates:
1. Creating an encryptor with a key
2. Encrypting a file with AES-256-GCM
3. Decrypting the file back
4. Verifying integrity
"""

from pathlib import Path
import tempfile

from src.core.encryption import MediaEncryptor


def main():
    # Create a sample file to encrypt
    sample_content = b"This is sensitive medical data that needs protection."

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create sample input file
        input_file = tmpdir / "sensitive_data.txt"
        input_file.write_bytes(sample_content)
        print(f"Created sample file: {input_file}")
        print(f"Original content: {sample_content.decode()}")
        print(f"Original size: {len(sample_content)} bytes\n")

        # Initialize encryptor (generates key if not exists)
        key_path = tmpdir / "encryption.key"
        encryptor = MediaEncryptor(str(key_path))
        print(f"Initialized encryptor with key: {key_path}\n")

        # Encrypt the file
        encrypted_file = tmpdir / "sensitive_data.enc"
        result = encryptor.encrypt_file(str(input_file), str(encrypted_file))

        print("=== Encryption Result ===")
        print(f"Original size: {result['original_size']:,} bytes")
        print(f"Encrypted size: {result['encrypted_size']:,} bytes")
        print(f"Algorithm: {result['algorithm']}")
        print(f"Checksum: {result['checksum'][:16]}...")
        print(f"Output: {encrypted_file}\n")

        # Show that encrypted content is unreadable
        encrypted_content = encrypted_file.read_bytes()
        print(f"Encrypted content (first 50 bytes): {encrypted_content[:50]}")
        print("(Note: This is unreadable ciphertext)\n")

        # Decrypt the file
        decrypted_file = tmpdir / "restored_data.txt"
        result = encryptor.decrypt_file(str(encrypted_file), str(decrypted_file))

        print("=== Decryption Result ===")
        print(f"Encrypted size: {result['encrypted_size']:,} bytes")
        print(f"Decrypted size: {result['decrypted_size']:,} bytes")
        print(f"Checksum valid: {result.get('checksum_valid', 'N/A')}")
        print(f"Output: {decrypted_file}\n")

        # Verify content matches original
        restored_content = decrypted_file.read_bytes()
        print(f"Restored content: {restored_content.decode()}")
        print(f"Content matches original: {restored_content == sample_content}")


if __name__ == "__main__":
    main()
