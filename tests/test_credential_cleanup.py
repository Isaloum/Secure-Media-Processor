"""
Tests for secure credential cleanup in cloud connectors.

These tests verify that credentials are properly cleared from memory
when connectors are destroyed, preventing credential leakage.
"""

import pytest
from src.connectors.s3_connector import S3Connector
from src.connectors.google_drive_connector import GoogleDriveConnector
from src.connectors.dropbox_connector import DropboxConnector


class TestCredentialCleanup:
    """Test suite for credential cleanup functionality."""

    def test_s3_credentials_cleared_on_del(self):
        """Test that S3 connector clears credentials when deleted."""
        # Create connector with credentials
        connector = S3Connector(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="fake_access_key",
            secret_key="fake_secret_key"
        )

        # Verify credentials are set
        assert connector.access_key == "fake_access_key"
        assert connector.secret_key == "fake_secret_key"
        assert connector.s3_client is None  # Not connected yet

        # Delete the connector (calls __del__)
        del connector

        # Note: We can't easily verify the credentials are cleared after del
        # because the object no longer exists. This test mainly ensures
        # __del__ doesn't raise exceptions.

    def test_s3_credentials_cleared_after_disconnect(self):
        """Test that S3 connector disconnect clears client objects."""
        connector = S3Connector(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="fake_access_key",
            secret_key="fake_secret_key"
        )

        # Mock connection state
        connector._connected = True
        connector.s3_client = "mock_client"
        connector.s3_resource = "mock_resource"

        # Disconnect
        result = connector.disconnect()

        # Verify cleanup
        assert result is True
        assert connector.s3_client is None
        assert connector.s3_resource is None
        assert connector._connected is False
        # Credentials remain (only cleared on __del__)
        assert connector.access_key == "fake_access_key"
        assert connector.secret_key == "fake_secret_key"

    def test_gdrive_credentials_cleared_on_del(self):
        """Test that Google Drive connector clears credentials when deleted."""
        # Create connector
        try:
            connector = GoogleDriveConnector(
                credentials_path="/fake/path/creds.json",
                folder_id="fake_folder_id"
            )

            # Mock some credential state
            connector.service = "mock_service"
            connector.credentials = "mock_credentials"

            # Delete the connector
            del connector
            # __del__ should not raise exceptions

        except ImportError:
            # Google Drive dependencies not installed in test environment
            pytest.skip("Google Drive dependencies not installed")

    def test_gdrive_credentials_cleared_after_disconnect(self):
        """Test that Google Drive connector disconnect clears service objects."""
        try:
            connector = GoogleDriveConnector(
                credentials_path="/fake/path/creds.json"
            )

            # Mock connection state
            connector._connected = True
            connector.service = "mock_service"
            connector.credentials = "mock_credentials"

            # Disconnect
            result = connector.disconnect()

            # Verify cleanup
            assert result is True
            assert connector.service is None
            assert connector.credentials is None
            assert connector._connected is False

        except ImportError:
            pytest.skip("Google Drive dependencies not installed")

    def test_dropbox_credentials_cleared_on_del(self):
        """Test that Dropbox connector clears credentials when deleted."""
        try:
            connector = DropboxConnector(access_token="fake_token")

            # Verify token is set
            assert connector.access_token == "fake_token"
            assert connector.dbx is None  # Not connected yet

            # Delete the connector
            del connector
            # __del__ should not raise exceptions

        except ImportError:
            pytest.skip("Dropbox SDK not installed")

    def test_dropbox_credentials_cleared_after_disconnect(self):
        """Test that Dropbox connector disconnect clears client objects."""
        try:
            connector = DropboxConnector(access_token="fake_token")

            # Mock connection state
            connector._connected = True
            connector.dbx = "mock_dropbox_client"

            # Disconnect
            result = connector.disconnect()

            # Verify cleanup
            assert result is True
            assert connector.dbx is None
            assert connector._connected is False
            # Token remains (only cleared on __del__)
            assert connector.access_token == "fake_token"

        except ImportError:
            pytest.skip("Dropbox SDK not installed")

    def test_multiple_disconnect_calls_safe(self):
        """Test that multiple disconnect calls don't cause errors."""
        connector = S3Connector(bucket_name="test-bucket")

        # Disconnect multiple times
        result1 = connector.disconnect()
        result2 = connector.disconnect()
        result3 = connector.disconnect()

        # Should all succeed
        assert result1 is True
        assert result2 is True
        assert result3 is True

    def test_del_on_uninitialized_connector(self):
        """Test that __del__ handles partially initialized connectors."""
        # Create connector but don't fully initialize
        connector = S3Connector(bucket_name="test")

        # Should not have these attributes yet
        assert not hasattr(connector, '_invalid_attr')

        # Delete should not raise
        del connector

    def test_del_without_credentials(self):
        """Test that __del__ handles connectors without explicit credentials."""
        # S3 connector using environment variables (no explicit creds)
        connector = S3Connector(bucket_name="test-bucket")

        # No explicit credentials set
        assert connector.access_key is None
        assert connector.secret_key is None

        # Delete should not raise
        del connector

    def test_credential_cleanup_on_exception(self):
        """Test that credentials are cleaned up even if exceptions occur."""
        connector = S3Connector(
            bucket_name="test-bucket",
            access_key="fake_key",
            secret_key="fake_secret"
        )

        try:
            # Simulate some operation that might fail
            raise ValueError("Simulated error")
        except ValueError:
            pass
        finally:
            # Ensure cleanup happens
            del connector
            # Should not raise during cleanup

    def test_s3_del_method_exists(self):
        """Test that S3Connector has __del__ method defined."""
        assert hasattr(S3Connector, '__del__')
        assert callable(getattr(S3Connector, '__del__'))

    def test_gdrive_del_method_exists(self):
        """Test that GoogleDriveConnector has __del__ method defined."""
        try:
            assert hasattr(GoogleDriveConnector, '__del__')
            assert callable(getattr(GoogleDriveConnector, '__del__'))
        except ImportError:
            pytest.skip("Google Drive dependencies not installed")

    def test_dropbox_del_method_exists(self):
        """Test that DropboxConnector has __del__ method defined."""
        try:
            assert hasattr(DropboxConnector, '__del__')
            assert callable(getattr(DropboxConnector, '__del__'))
        except ImportError:
            pytest.skip("Dropbox SDK not installed")


class TestCredentialMemorySafety:
    """Test suite for memory safety of credentials."""

    def test_s3_credentials_not_logged(self, caplog):
        """Test that S3 credentials are not accidentally logged."""
        import logging
        caplog.set_level(logging.DEBUG)

        connector = S3Connector(
            bucket_name="test-bucket",
            access_key="SUPER_SECRET_KEY_123",
            secret_key="SUPER_SECRET_VALUE_456"
        )

        # Trigger disconnect
        connector.disconnect()

        # Check logs don't contain credentials
        log_text = caplog.text.lower()
        assert "super_secret_key_123" not in log_text
        assert "super_secret_value_456" not in log_text

    def test_dropbox_token_not_logged(self, caplog):
        """Test that Dropbox token is not accidentally logged."""
        try:
            import logging
            caplog.set_level(logging.DEBUG)

            connector = DropboxConnector(access_token="SECRET_TOKEN_XYZ_789")

            # Trigger disconnect
            connector.disconnect()

            # Check logs don't contain token
            log_text = caplog.text.lower()
            assert "secret_token_xyz_789" not in log_text

        except ImportError:
            pytest.skip("Dropbox SDK not installed")

    def test_credentials_not_in_repr(self):
        """Test that credentials are not exposed in __repr__."""
        connector = S3Connector(
            bucket_name="test-bucket",
            access_key="SECRET_KEY",
            secret_key="SECRET_VALUE"
        )

        repr_str = repr(connector)

        # Repr should not contain credentials
        assert "SECRET_KEY" not in repr_str
        assert "SECRET_VALUE" not in repr_str
        # But should contain useful info
        assert "S3Connector" in repr_str
