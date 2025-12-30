"""Test suite for encryption module."""

import pytest
from pathlib import Path
import tempfile
import os
from src.encryption import MediaEncryptor


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is a test file for encryption.")
    return file_path


@pytest.fixture
def encryptor(temp_dir):
    """Create encryptor instance."""
    key_path = temp_dir / "test.key"
    return MediaEncryptor(key_path)


def test_key_generation(temp_dir):
    """Test encryption key generation."""
    key_path = temp_dir / "test.key"
    encryptor = MediaEncryptor(key_path)
    
    assert key_path.exists()
    assert len(key_path.read_bytes()) == 32  # 256 bits


def test_key_loading(temp_dir):
    """Test loading existing key."""
    key_path = temp_dir / "test.key"
    
    # Create first encryptor
    encryptor1 = MediaEncryptor(key_path)
    key1 = encryptor1.key
    
    # Create second encryptor with same key path
    encryptor2 = MediaEncryptor(key_path)
    key2 = encryptor2.key
    
    assert key1 == key2


def test_encrypt_decrypt(encryptor, sample_file, temp_dir):
    """Test encryption and decryption."""
    encrypted_file = temp_dir / "encrypted.bin"
    decrypted_file = temp_dir / "decrypted.txt"
    
    # Encrypt
    encrypt_result = encryptor.encrypt_file(sample_file, encrypted_file)
    assert encrypted_file.exists()
    assert encrypt_result['original_size'] > 0
    assert encrypt_result['encrypted_size'] > encrypt_result['original_size']
    
    # Decrypt
    decrypt_result = encryptor.decrypt_file(encrypted_file, decrypted_file)
    assert decrypted_file.exists()
    assert decrypt_result['decrypted_size'] == encrypt_result['original_size']
    
    # Verify content
    assert sample_file.read_text() == decrypted_file.read_text()


def test_secure_delete(encryptor, temp_dir):
    """Test secure file deletion."""
    test_file = temp_dir / "to_delete.txt"
    test_file.write_text("Delete me securely")
    
    assert test_file.exists()
    
    encryptor.secure_delete(test_file)
    
    assert not test_file.exists()


def test_encryption_different_files(encryptor, temp_dir):
    """Test that same content produces different ciphertext."""
    file1 = temp_dir / "file1.txt"
    file2 = temp_dir / "file2.txt"
    file1.write_text("Same content")
    file2.write_text("Same content")
    
    encrypted1 = temp_dir / "enc1.bin"
    encrypted2 = temp_dir / "enc2.bin"
    
    encryptor.encrypt_file(file1, encrypted1)
    encryptor.encrypt_file(file2, encrypted2)
    
    # Different nonces should produce different ciphertext
    assert encrypted1.read_bytes() != encrypted2.read_bytes()
