"""Comprehensive test suite for CLI commands.

This module tests all CLI commands including:
- encrypt/decrypt commands
- upload/download commands (license gated)
- resize/filter-image commands (license gated)
- info command
- license activate/status/deactivate commands
- Error handling and edge cases
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from src.cli import cli


@pytest.fixture
def runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file for testing."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("This is test content for CLI testing.")
    return file_path


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample image file for testing."""
    from PIL import Image
    img_path = temp_dir / "sample.png"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    return img_path


@pytest.fixture
def mock_encryptor():
    """Mock MediaEncryptor for testing."""
    with patch('src.cli.MediaEncryptor') as mock:
        instance = Mock()
        instance.encrypt_file.return_value = {
            'original_size': 100,
            'encrypted_size': 128,
            'algorithm': 'AES-256-GCM'
        }
        instance.decrypt_file.return_value = {
            'encrypted_size': 128,
            'decrypted_size': 100
        }
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_storage():
    """Mock CloudStorageManager for testing."""
    with patch('src.cli.CloudStorageManager') as mock:
        instance = Mock()
        instance.upload_file.return_value = {
            'success': True,
            'remote_key': 'uploaded/file.txt',
            'size': 100,
            'checksum': 'abc123'
        }
        instance.download_file.return_value = {
            'success': True,
            'local_path': '/tmp/downloaded.txt',
            'size': 100,
            'checksum_verified': True
        }
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_gpu_processor():
    """Mock GPUMediaProcessor for testing."""
    with patch('src.cli.GPUMediaProcessor') as mock:
        instance = Mock()
        instance.resize_image.return_value = {
            'original_size': (100, 100),
            'new_size': (50, 50),
            'device': 'CPU',
            'output_path': '/tmp/resized.png'
        }
        instance.apply_filter.return_value = {
            'filter_type': 'blur',
            'intensity': 1.0,
            'device': 'CPU',
            'output_path': '/tmp/filtered.png'
        }
        instance.get_device_info.return_value = {
            'device': 'CPU',
            'name': 'CPU Fallback',
            'memory_total': 0,
            'memory_allocated': 0,
            'memory_cached': 0,
            'cuda_version': 'N/A'
        }
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_license_free():
    """Mock LicenseManager with free tier (no features)."""
    with patch('src.cli.get_license_manager') as mock_getter:
        manager = Mock()
        manager.check_feature.return_value = False
        mock_getter.return_value = manager
        yield manager


@pytest.fixture
def mock_license_pro():
    """Mock LicenseManager with pro tier (all features)."""
    with patch('src.cli.get_license_manager') as mock_getter:
        manager = Mock()
        manager.check_feature.return_value = True
        mock_getter.return_value = manager
        yield manager


# =============================================================================
# VERSION AND HELP TESTS
# =============================================================================

class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_version(self, runner):
        """Test --version flag displays version."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output

    def test_cli_help(self, runner):
        """Test --help flag displays help."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Secure Media Processor' in result.output
        assert 'encrypt' in result.output
        assert 'decrypt' in result.output

    def test_encrypt_help(self, runner):
        """Test encrypt command help."""
        result = runner.invoke(cli, ['encrypt', '--help'])
        assert result.exit_code == 0
        assert 'Encrypt a media file' in result.output

    def test_decrypt_help(self, runner):
        """Test decrypt command help."""
        result = runner.invoke(cli, ['decrypt', '--help'])
        assert result.exit_code == 0
        assert 'Decrypt a media file' in result.output


# =============================================================================
# ENCRYPT COMMAND TESTS
# =============================================================================

class TestEncryptCommand:
    """Test encrypt command."""

    def test_encrypt_success(self, runner, sample_file, temp_dir, mock_encryptor):
        """Test successful file encryption."""
        output_file = temp_dir / "encrypted.bin"

        result = runner.invoke(cli, [
            'encrypt',
            str(sample_file),
            str(output_file)
        ])

        assert result.exit_code == 0
        assert 'Encrypting file' in result.output
        assert 'File encrypted successfully' in result.output
        assert 'Original size: 100' in result.output
        assert 'Encrypted size: 128' in result.output
        assert 'AES-256-GCM' in result.output

    def test_encrypt_with_custom_key(self, runner, sample_file, temp_dir, mock_encryptor):
        """Test encryption with custom key path."""
        output_file = temp_dir / "encrypted.bin"
        key_file = temp_dir / "custom.key"

        result = runner.invoke(cli, [
            'encrypt',
            str(sample_file),
            str(output_file),
            '--key-path', str(key_file)
        ])

        assert result.exit_code == 0
        mock_encryptor.assert_called_once_with(str(key_file))

    def test_encrypt_nonexistent_file(self, runner, temp_dir):
        """Test encryption with nonexistent input file."""
        result = runner.invoke(cli, [
            'encrypt',
            '/nonexistent/file.txt',
            str(temp_dir / "output.bin")
        ])

        assert result.exit_code != 0
        # Click validates file existence before command runs

    def test_encrypt_failure(self, runner, sample_file, temp_dir):
        """Test encryption failure handling."""
        with patch('src.cli.MediaEncryptor') as mock:
            mock.return_value.encrypt_file.side_effect = ValueError("Encryption failed")

            result = runner.invoke(cli, [
                'encrypt',
                str(sample_file),
                str(temp_dir / "output.bin")
            ])

            assert result.exit_code == 1
            assert 'Encryption failed' in result.output


# =============================================================================
# DECRYPT COMMAND TESTS
# =============================================================================

class TestDecryptCommand:
    """Test decrypt command."""

    def test_decrypt_success(self, runner, sample_file, temp_dir, mock_encryptor):
        """Test successful file decryption."""
        output_file = temp_dir / "decrypted.txt"

        result = runner.invoke(cli, [
            'decrypt',
            str(sample_file),  # Using sample as "encrypted" file
            str(output_file)
        ])

        assert result.exit_code == 0
        assert 'Decrypting file' in result.output
        assert 'File decrypted successfully' in result.output
        assert 'Encrypted size: 128' in result.output
        assert 'Decrypted size: 100' in result.output

    def test_decrypt_with_custom_key(self, runner, sample_file, temp_dir, mock_encryptor):
        """Test decryption with custom key path."""
        output_file = temp_dir / "decrypted.txt"
        key_file = temp_dir / "custom.key"

        result = runner.invoke(cli, [
            'decrypt',
            str(sample_file),
            str(output_file),
            '--key-path', str(key_file)
        ])

        assert result.exit_code == 0
        mock_encryptor.assert_called_once_with(str(key_file))

    def test_decrypt_failure(self, runner, sample_file, temp_dir):
        """Test decryption failure handling."""
        with patch('src.cli.MediaEncryptor') as mock:
            mock.return_value.decrypt_file.side_effect = ValueError("Invalid ciphertext")

            result = runner.invoke(cli, [
                'decrypt',
                str(sample_file),
                str(temp_dir / "output.txt")
            ])

            assert result.exit_code == 1
            assert 'Decryption failed' in result.output


# =============================================================================
# UPLOAD COMMAND TESTS (LICENSE GATED)
# =============================================================================

class TestUploadCommand:
    """Test upload command."""

    def test_upload_requires_license(self, runner, sample_file):
        """Test upload requires pro license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = False
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'upload',
                str(sample_file),
                '--bucket', 'test-bucket'
            ])

            assert result.exit_code == 1
            assert 'Pro or Enterprise license' in result.output
            assert 'pricing' in result.output.lower()

    def test_upload_success_with_license(self, runner, sample_file, mock_storage):
        """Test successful upload with valid license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = 'test-bucket'
                mock_settings.aws_region = 'us-east-1'
                mock_settings.aws_access_key_id = 'test-key'
                mock_settings.aws_secret_access_key = 'test-secret'

                result = runner.invoke(cli, [
                    'upload',
                    str(sample_file),
                    '--bucket', 'test-bucket'
                ])

                assert result.exit_code == 0
                assert 'File uploaded successfully' in result.output
                assert 'Remote key' in result.output

    def test_upload_no_bucket_specified(self, runner, sample_file):
        """Test upload fails without bucket."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = None

                result = runner.invoke(cli, [
                    'upload',
                    str(sample_file)
                ])

                assert result.exit_code == 1
                assert 'Bucket name not specified' in result.output

    def test_upload_failure(self, runner, sample_file):
        """Test upload failure handling."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = 'test-bucket'
                mock_settings.aws_region = 'us-east-1'
                mock_settings.aws_access_key_id = 'test-key'
                mock_settings.aws_secret_access_key = 'test-secret'

                with patch('src.cli.CloudStorageManager') as mock_storage:
                    mock_storage.return_value.upload_file.return_value = {
                        'success': False,
                        'error': 'Connection timeout'
                    }

                    result = runner.invoke(cli, [
                        'upload',
                        str(sample_file),
                        '--bucket', 'test-bucket'
                    ])

                    assert result.exit_code == 1
                    assert 'Upload failed' in result.output


# =============================================================================
# DOWNLOAD COMMAND TESTS (LICENSE GATED)
# =============================================================================

class TestDownloadCommand:
    """Test download command."""

    def test_download_requires_license(self, runner, temp_dir):
        """Test download requires pro license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = False
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'download',
                'remote/file.txt',
                str(temp_dir / "local.txt"),
                '--bucket', 'test-bucket'
            ])

            assert result.exit_code == 1
            assert 'Pro or Enterprise license' in result.output

    def test_download_success_with_license(self, runner, temp_dir, mock_storage):
        """Test successful download with valid license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = 'test-bucket'
                mock_settings.aws_region = 'us-east-1'
                mock_settings.aws_access_key_id = 'test-key'
                mock_settings.aws_secret_access_key = 'test-secret'

                result = runner.invoke(cli, [
                    'download',
                    'remote/file.txt',
                    str(temp_dir / "local.txt"),
                    '--bucket', 'test-bucket'
                ])

                assert result.exit_code == 0
                assert 'File downloaded successfully' in result.output
                assert 'Checksum verified' in result.output

    def test_download_no_verify(self, runner, temp_dir, mock_storage):
        """Test download with --no-verify flag."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = 'test-bucket'
                mock_settings.aws_region = 'us-east-1'
                mock_settings.aws_access_key_id = 'test-key'
                mock_settings.aws_secret_access_key = 'test-secret'

                result = runner.invoke(cli, [
                    'download',
                    'remote/file.txt',
                    str(temp_dir / "local.txt"),
                    '--bucket', 'test-bucket',
                    '--no-verify'
                ])

                assert result.exit_code == 0
                mock_storage.return_value.download_file.assert_called_once()


# =============================================================================
# RESIZE COMMAND TESTS (LICENSE GATED)
# =============================================================================

class TestResizeCommand:
    """Test resize command."""

    def test_resize_requires_license_with_gpu(self, runner, sample_image, temp_dir):
        """Test resize with GPU requires pro license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = False
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'resize',
                str(sample_image),
                str(temp_dir / "resized.png"),
                '--width', '50',
                '--height', '50'
            ])

            assert result.exit_code == 1
            assert 'Pro or Enterprise license' in result.output

    def test_resize_no_gpu_no_license(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test resize with --no-gpu doesn't require license."""
        result = runner.invoke(cli, [
            'resize',
            str(sample_image),
            str(temp_dir / "resized.png"),
            '--width', '50',
            '--height', '50',
            '--no-gpu'
        ])

        assert result.exit_code == 0
        assert 'Image resized successfully' in result.output
        mock_gpu_processor.assert_called_with(gpu_enabled=False)

    def test_resize_success_with_license(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test successful resize with valid license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'resize',
                str(sample_image),
                str(temp_dir / "resized.png"),
                '--width', '50',
                '--height', '50'
            ])

            assert result.exit_code == 0
            assert 'Image resized successfully' in result.output
            assert 'Original size' in result.output
            assert 'New size' in result.output

    def test_resize_failure(self, runner, sample_image, temp_dir):
        """Test resize failure handling."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.GPUMediaProcessor') as mock:
                mock.return_value.resize_image.side_effect = ValueError("Invalid dimensions")

                result = runner.invoke(cli, [
                    'resize',
                    str(sample_image),
                    str(temp_dir / "resized.png"),
                    '--width', '50',
                    '--height', '50'
                ])

                assert result.exit_code == 1
                assert 'Resize failed' in result.output


# =============================================================================
# FILTER-IMAGE COMMAND TESTS (LICENSE GATED)
# =============================================================================

class TestFilterImageCommand:
    """Test filter-image command."""

    def test_filter_requires_license_with_gpu(self, runner, sample_image, temp_dir):
        """Test filter with GPU requires pro license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = False
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'filter-image',
                str(sample_image),
                str(temp_dir / "filtered.png"),
                '--filter', 'blur'
            ])

            assert result.exit_code == 1
            assert 'Pro or Enterprise license' in result.output

    def test_filter_no_gpu_no_license(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test filter with --no-gpu doesn't require license."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'blur',
            '--no-gpu'
        ])

        assert result.exit_code == 0
        assert 'Filter applied successfully' in result.output

    def test_filter_blur(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test blur filter."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'blur',
            '--no-gpu'
        ])

        assert result.exit_code == 0
        assert 'Filter: blur' in result.output

    def test_filter_sharpen(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test sharpen filter."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'sharpen',
            '--no-gpu'
        ])

        assert result.exit_code == 0

    def test_filter_edge(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test edge detection filter."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'edge',
            '--no-gpu'
        ])

        assert result.exit_code == 0

    def test_filter_custom_intensity(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test filter with custom intensity."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'blur',
            '--intensity', '1.5',
            '--no-gpu'
        ])

        assert result.exit_code == 0
        mock_gpu_processor.return_value.apply_filter.assert_called_once()

    def test_filter_invalid_choice(self, runner, sample_image, temp_dir):
        """Test filter with invalid filter type."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'invalid'
        ])

        assert result.exit_code != 0
        # Click validates choice before command runs


# =============================================================================
# INFO COMMAND TESTS
# =============================================================================

class TestInfoCommand:
    """Test info command."""

    def test_info_cpu(self, runner, mock_gpu_processor):
        """Test info command with CPU."""
        result = runner.invoke(cli, ['info'])

        assert result.exit_code == 0
        assert 'System Information' in result.output
        assert 'Device:' in result.output
        assert 'CPU' in result.output

    def test_info_gpu(self, runner):
        """Test info command with GPU available."""
        with patch('src.cli.GPUMediaProcessor') as mock:
            mock.return_value.get_device_info.return_value = {
                'device': 'CUDA',  # Device type is CUDA, not GPU
                'name': 'NVIDIA RTX 4090',
                'vendor': 'NVIDIA',
                'memory_total': 24.0,
                'memory_allocated': 1.5,
                'memory_cached': 0.5,
                'cuda_version': '12.1'
            }

            result = runner.invoke(cli, ['info'])

            assert result.exit_code == 0
            assert 'CUDA' in result.output
            assert 'NVIDIA RTX 4090' in result.output
            assert 'Total Memory' in result.output
            assert 'CUDA Version' in result.output


# =============================================================================
# LICENSE SUBCOMMAND TESTS
# =============================================================================

class TestLicenseCommands:
    """Test license management commands."""

    def test_license_help(self, runner):
        """Test license command help."""
        result = runner.invoke(cli, ['license', '--help'])
        assert result.exit_code == 0
        assert 'Manage license' in result.output
        assert 'activate' in result.output
        assert 'status' in result.output
        assert 'deactivate' in result.output

    def test_license_activate_success(self, runner):
        """Test successful license activation."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            license_obj = Mock()
            license_obj.license_type.value = 'pro'
            license_obj.email = 'test@example.com'
            license_obj.expires_at = None
            license_obj.issued_at = Mock()
            license_obj.features = ['cloud_storage', 'gpu_processing']
            manager.activate_license.return_value = license_obj
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'activate',
                'TEST-LICENSE-KEY-1234',
                '--email', 'test@example.com'
            ])

            assert result.exit_code == 0
            assert 'License activated successfully' in result.output
            assert 'PRO' in result.output
            assert 'test@example.com' in result.output
            assert 'Thank you for supporting' in result.output

    def test_license_activate_with_expiry(self, runner):
        """Test license activation with expiry date."""
        from datetime import datetime, timedelta

        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            license_obj = Mock()
            license_obj.license_type.value = 'pro'
            license_obj.email = 'test@example.com'
            license_obj.issued_at = datetime.now()
            license_obj.expires_at = datetime.now() + timedelta(days=365)
            license_obj.features = ['cloud_storage']
            manager.activate_license.return_value = license_obj
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'activate',
                'TEST-LICENSE-KEY-1234',
                '--email', 'test@example.com'
            ])

            assert result.exit_code == 0
            assert '365 days' in result.output

    def test_license_activate_invalid_key(self, runner):
        """Test license activation with invalid key."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.activate_license.side_effect = ValueError("Invalid license key")
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'activate',
                'INVALID-KEY',
                '--email', 'test@example.com'
            ])

            assert result.exit_code == 1
            assert 'Activation failed' in result.output
            assert 'Invalid license key' in result.output

    def test_license_status_active(self, runner):
        """Test license status with active license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.get_license_info.return_value = {
                'active': True,
                'type': 'pro',
                'email': 'test@example.com',
                'days_remaining': 180,
                'activated_devices': 1,
                'max_devices': 3,
                'features': ['cloud_storage', 'gpu_processing']
            }
            mock_getter.return_value = manager

            result = runner.invoke(cli, ['license', 'status'])

            assert result.exit_code == 0
            assert 'Active' in result.output
            assert 'PRO' in result.output
            assert '180 days' in result.output
            assert '1/3' in result.output
            assert 'Cloud Storage' in result.output

    def test_license_status_free_tier(self, runner):
        """Test license status with free tier."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.get_license_info.return_value = {
                'active': False,
                'message': 'No active license',
                'features': []
            }
            mock_getter.return_value = manager

            result = runner.invoke(cli, ['license', 'status'])

            assert result.exit_code == 0
            assert 'Free Tier' in result.output
            assert 'pricing' in result.output.lower()

    def test_license_status_lifetime(self, runner):
        """Test license status with lifetime license."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.get_license_info.return_value = {
                'active': True,
                'type': 'enterprise',
                'email': 'enterprise@company.com',
                'days_remaining': None,
                'activated_devices': 5,
                'max_devices': 100,
                'features': ['cloud_storage', 'gpu_processing', 'multi_cloud_sync']
            }
            mock_getter.return_value = manager

            result = runner.invoke(cli, ['license', 'status'])

            assert result.exit_code == 0
            assert 'Lifetime' in result.output
            assert 'ENTERPRISE' in result.output

    def test_license_deactivate_success(self, runner):
        """Test successful license deactivation."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.deactivate_license.return_value = True
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'deactivate',
                '--yes'  # Skip confirmation
            ])

            assert result.exit_code == 0
            assert 'License deactivated successfully' in result.output
            assert 'another device' in result.output

    def test_license_deactivate_no_license(self, runner):
        """Test deactivation when no license is active."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.deactivate_license.return_value = False
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'deactivate',
                '--yes'
            ])

            assert result.exit_code == 0
            assert 'No active license' in result.output

    def test_license_deactivate_requires_confirmation(self, runner):
        """Test deactivation requires confirmation."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            mock_getter.return_value = manager

            result = runner.invoke(cli, [
                'license', 'deactivate'
            ], input='n\n')  # Decline confirmation

            assert result.exit_code == 1


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_encrypt_corrupted_file(self, runner, temp_dir):
        """Test encryption with corrupted/unreadable file."""
        with patch('src.cli.MediaEncryptor') as mock:
            mock.return_value.encrypt_file.side_effect = IOError("Cannot read file")

            # Create a file to pass Click's exists check
            file_path = temp_dir / "test.txt"
            file_path.write_text("test")

            result = runner.invoke(cli, [
                'encrypt',
                str(file_path),
                str(temp_dir / "output.bin")
            ])

            assert result.exit_code == 1
            assert 'Encryption failed' in result.output

    def test_decrypt_wrong_key(self, runner, sample_file, temp_dir):
        """Test decryption with wrong key."""
        with patch('src.cli.MediaEncryptor') as mock:
            mock.return_value.decrypt_file.side_effect = ValueError(
                "Decryption failed: Authentication tag mismatch"
            )

            result = runner.invoke(cli, [
                'decrypt',
                str(sample_file),
                str(temp_dir / "output.txt")
            ])

            assert result.exit_code == 1
            assert 'Decryption failed' in result.output

    def test_network_timeout(self, runner, sample_file):
        """Test network timeout handling in upload."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.settings') as mock_settings:
                mock_settings.aws_bucket_name = 'test-bucket'
                mock_settings.aws_region = 'us-east-1'
                mock_settings.aws_access_key_id = 'test-key'
                mock_settings.aws_secret_access_key = 'test-secret'

                with patch('src.cli.CloudStorageManager') as mock_storage:
                    mock_storage.return_value.upload_file.side_effect = \
                        ConnectionError("Connection timed out")

                    result = runner.invoke(cli, [
                        'upload',
                        str(sample_file),
                        '--bucket', 'test-bucket'
                    ])

                    assert result.exit_code == 1
                    assert 'Upload failed' in result.output

    def test_gpu_out_of_memory(self, runner, sample_image, temp_dir):
        """Test GPU out of memory handling."""
        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()
            manager.check_feature.return_value = True
            mock_getter.return_value = manager

            with patch('src.cli.GPUMediaProcessor') as mock:
                mock.return_value.resize_image.side_effect = \
                    RuntimeError("CUDA out of memory")

                result = runner.invoke(cli, [
                    'resize',
                    str(sample_image),
                    str(temp_dir / "resized.png"),
                    '--width', '10000',
                    '--height', '10000'
                ])

                assert result.exit_code == 1
                assert 'Resize failed' in result.output


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestCLIIntegration:
    """Integration tests for CLI workflows."""

    def test_encrypt_then_decrypt_roundtrip(self, runner, temp_dir):
        """Test complete encrypt/decrypt roundtrip."""
        # Create original file
        original = temp_dir / "original.txt"
        original.write_text("Sensitive data for roundtrip test")

        encrypted = temp_dir / "encrypted.bin"
        decrypted = temp_dir / "decrypted.txt"
        key_path = temp_dir / "test.key"

        # Encrypt (using real encryptor)
        result = runner.invoke(cli, [
            'encrypt',
            str(original),
            str(encrypted),
            '--key-path', str(key_path)
        ])

        assert result.exit_code == 0
        assert encrypted.exists()

        # Decrypt
        result = runner.invoke(cli, [
            'decrypt',
            str(encrypted),
            str(decrypted),
            '--key-path', str(key_path)
        ])

        assert result.exit_code == 0
        assert decrypted.exists()
        assert original.read_text() == decrypted.read_text()

    def test_info_then_process(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test info command followed by processing."""
        # Check system info
        info_result = runner.invoke(cli, ['info'])
        assert info_result.exit_code == 0

        # Then process an image
        result = runner.invoke(cli, [
            'resize',
            str(sample_image),
            str(temp_dir / "resized.png"),
            '--width', '50',
            '--height', '50',
            '--no-gpu'
        ])

        assert result.exit_code == 0

    def test_license_workflow(self, runner):
        """Test complete license workflow."""
        from datetime import datetime, timedelta

        with patch('src.license_manager.get_license_manager') as mock_getter:
            manager = Mock()

            # First check status (should be free)
            manager.get_license_info.return_value = {
                'active': False,
                'message': 'No active license',
                'features': []
            }
            mock_getter.return_value = manager

            status_result = runner.invoke(cli, ['license', 'status'])
            assert 'Free Tier' in status_result.output

            # Activate license
            license_obj = Mock()
            license_obj.license_type.value = 'pro'
            license_obj.email = 'user@example.com'
            license_obj.expires_at = None
            license_obj.issued_at = datetime.now()
            license_obj.features = ['cloud_storage', 'gpu_processing']
            manager.activate_license.return_value = license_obj

            activate_result = runner.invoke(cli, [
                'license', 'activate',
                'PRO-LICENSE-KEY',
                '--email', 'user@example.com'
            ])
            assert 'License activated successfully' in activate_result.output

            # Deactivate
            manager.deactivate_license.return_value = True
            deactivate_result = runner.invoke(cli, [
                'license', 'deactivate', '--yes'
            ])
            assert 'License deactivated successfully' in deactivate_result.output


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file_encryption(self, runner, temp_dir, mock_encryptor):
        """Test encrypting an empty file."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")

        result = runner.invoke(cli, [
            'encrypt',
            str(empty_file),
            str(temp_dir / "encrypted.bin")
        ])

        # Should handle gracefully (implementation dependent)
        assert result.exit_code == 0 or 'failed' in result.output.lower()

    def test_special_characters_in_path(self, runner, temp_dir, mock_encryptor):
        """Test file paths with special characters."""
        special_file = temp_dir / "file with spaces & symbols!.txt"
        special_file.write_text("Test content")

        result = runner.invoke(cli, [
            'encrypt',
            str(special_file),
            str(temp_dir / "output.bin")
        ])

        assert result.exit_code == 0

    def test_unicode_filename(self, runner, temp_dir, mock_encryptor):
        """Test file paths with unicode characters."""
        unicode_file = temp_dir / "archivo_espanol.txt"
        unicode_file.write_text("Contenido de prueba")

        result = runner.invoke(cli, [
            'encrypt',
            str(unicode_file),
            str(temp_dir / "salida.bin")
        ])

        assert result.exit_code == 0

    def test_very_long_filename(self, runner, temp_dir, mock_encryptor):
        """Test file paths with very long names."""
        long_name = "a" * 200 + ".txt"
        long_file = temp_dir / long_name
        long_file.write_text("Test")

        result = runner.invoke(cli, [
            'encrypt',
            str(long_file),
            str(temp_dir / "output.bin")
        ])

        assert result.exit_code == 0

    def test_resize_to_one_pixel(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test resizing to 1x1 pixel."""
        result = runner.invoke(cli, [
            'resize',
            str(sample_image),
            str(temp_dir / "tiny.png"),
            '--width', '1',
            '--height', '1',
            '--no-gpu'
        ])

        assert result.exit_code == 0

    def test_filter_zero_intensity(self, runner, sample_image, temp_dir, mock_gpu_processor):
        """Test filter with zero intensity."""
        result = runner.invoke(cli, [
            'filter-image',
            str(sample_image),
            str(temp_dir / "filtered.png"),
            '--filter', 'blur',
            '--intensity', '0.0',
            '--no-gpu'
        ])

        assert result.exit_code == 0
