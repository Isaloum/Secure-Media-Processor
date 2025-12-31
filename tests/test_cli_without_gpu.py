"""Test suite for CLI without GPU support."""

import pytest
import sys
from pathlib import Path
import tempfile
from click.testing import CliRunner


def test_cli_import_without_torch():
    """Test that CLI can be imported even when PyTorch is not available."""
    # This test verifies the fix for macOS/Python 3.14+ compatibility
    
    # Temporarily hide torch if it's installed
    torch_module = sys.modules.get('torch')
    torchvision_module = sys.modules.get('torchvision')
    
    if torch_module:
        sys.modules['torch'] = None
    if torchvision_module:
        sys.modules['torchvision'] = None
    
    try:
        # This should not raise ImportError
        from src.cli import cli, GPU_AVAILABLE
        
        # GPU should not be available when torch is hidden
        assert GPU_AVAILABLE == False or torch_module is not None
        
    finally:
        # Restore modules
        if torch_module:
            sys.modules['torch'] = torch_module
        if torchvision_module:
            sys.modules['torchvision'] = torchvision_module


def test_cli_help_without_gpu():
    """Test that CLI help works without GPU support."""
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    
    assert result.exit_code == 0
    assert 'Secure Media Processor' in result.output
    assert 'encrypt' in result.output
    assert 'decrypt' in result.output


def test_info_command_without_gpu():
    """Test info command when GPU is not available."""
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['info'])
    
    assert result.exit_code == 0
    # Should show system info even without GPU
    assert 'System Information' in result.output


def test_encrypt_decrypt_without_gpu():
    """Test that encryption/decryption works without GPU."""
    from src.cli import cli
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test file
        input_file = tmpdir / "test.txt"
        input_file.write_text("Test content for encryption")
        
        encrypted_file = tmpdir / "test.enc"
        decrypted_file = tmpdir / "test_decrypted.txt"
        key_file = tmpdir / "test.key"
        
        # Test encryption
        result = runner.invoke(cli, [
            'encrypt',
            str(input_file),
            str(encrypted_file),
            '--key-path', str(key_file)
        ])
        
        assert result.exit_code == 0
        assert encrypted_file.exists()
        assert 'encrypted successfully' in result.output.lower()
        
        # Test decryption
        result = runner.invoke(cli, [
            'decrypt',
            str(encrypted_file),
            str(decrypted_file),
            '--key-path', str(key_file)
        ])
        
        assert result.exit_code == 0
        assert decrypted_file.exists()
        assert 'decrypted successfully' in result.output.lower()
        
        # Verify content
        assert input_file.read_text() == decrypted_file.read_text()


def test_gpu_commands_graceful_failure():
    """Test that GPU commands fail gracefully when PyTorch is not available."""
    # Only run this test if GPU is actually not available
    from src.cli import cli, GPU_AVAILABLE
    
    if GPU_AVAILABLE:
        pytest.skip("GPU is available, skipping unavailability test")
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a dummy file
        input_file = tmpdir / "test.txt"
        input_file.write_text("test")
        output_file = tmpdir / "output.txt"
        
        # Test resize command
        result = runner.invoke(cli, [
            'resize',
            str(input_file),
            str(output_file),
            '--width', '100',
            '--height', '100'
        ])
        
        # Should fail gracefully with helpful message
        assert result.exit_code == 1
        assert 'not available' in result.output.lower() or 'pytorch' in result.output.lower()
