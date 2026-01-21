"""
Tests for rate limiting functionality in cloud connectors.

These tests verify that rate limiting prevents API abuse and
excessive costs from cloud provider API calls.
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.rate_limiter import RateLimiter, RateLimitConfig
from src.connectors.s3_connector import S3Connector


class TestRateLimiter:
    """Test suite for token bucket rate limiter."""

    def test_rate_limiter_initialization(self):
        """Test that rate limiter initializes with correct defaults."""
        limiter = RateLimiter(rate=10.0)

        assert limiter.rate == 10.0
        assert limiter.capacity == 20.0  # Default is rate * 2
        assert limiter.tokens == 20.0  # Starts at capacity

    def test_rate_limiter_custom_capacity(self):
        """Test rate limiter with custom capacity."""
        limiter = RateLimiter(rate=5.0, capacity=10.0)

        assert limiter.rate == 5.0
        assert limiter.capacity == 10.0
        assert limiter.tokens == 10.0

    def test_acquire_single_token(self):
        """Test acquiring a single token."""
        limiter = RateLimiter(rate=10.0)

        # Should succeed immediately
        result = limiter.acquire(tokens=1, blocking=False)
        assert result is True
        assert limiter.tokens < 20.0  # One token consumed

    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens at once."""
        limiter = RateLimiter(rate=10.0, capacity=20.0)

        # Acquire 5 tokens
        result = limiter.acquire(tokens=5, blocking=False)
        assert result is True
        assert limiter.tokens == 15.0

    def test_acquire_fails_when_insufficient_tokens(self):
        """Test that acquire fails when not enough tokens available."""
        limiter = RateLimiter(rate=10.0, capacity=20.0)

        # Consume most tokens
        limiter.acquire(tokens=18, blocking=False)

        # Try to acquire more than available
        result = limiter.acquire(tokens=5, blocking=False)
        assert result is False

    def test_tokens_refill_over_time(self):
        """Test that tokens refill based on elapsed time."""
        limiter = RateLimiter(rate=10.0, capacity=20.0)

        # Consume all tokens
        limiter.acquire(tokens=20, blocking=False)
        assert limiter.tokens == 0.0

        # Wait for tokens to refill (100ms = 1 token at 10/sec)
        time.sleep(0.2)  # 200ms = ~2 tokens

        available = limiter.get_available_tokens()
        assert available >= 1.0  # At least 1 token should have refilled
        assert available <= 3.0  # But not more than ~2-3 tokens

    def test_blocking_acquire_waits_for_tokens(self):
        """Test that blocking acquire waits for tokens to become available."""
        limiter = RateLimiter(rate=10.0, capacity=20.0)

        # Consume all tokens
        limiter.acquire(tokens=20, blocking=False)

        start = time.monotonic()
        # This should block briefly until tokens refill
        result = limiter.acquire(tokens=1, blocking=True, timeout=1.0)
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed > 0.05  # Should have waited at least 50ms
        assert elapsed < 1.0   # But not the full timeout

    def test_acquire_timeout(self):
        """Test that acquire respects timeout."""
        limiter = RateLimiter(rate=1.0, capacity=1.0)  # Very slow rate

        # Consume all tokens
        limiter.acquire(tokens=1, blocking=False)

        start = time.monotonic()
        # Try to acquire many tokens with short timeout
        result = limiter.acquire(tokens=10, blocking=True, timeout=0.2)
        elapsed = time.monotonic() - start

        assert result is False  # Should timeout
        assert 0.15 <= elapsed <= 0.3  # Should be close to timeout

    def test_try_acquire_never_blocks(self):
        """Test that try_acquire never blocks."""
        limiter = RateLimiter(rate=1.0, capacity=1.0)

        # Consume all tokens
        limiter.acquire(tokens=1, blocking=False)

        start = time.monotonic()
        result = limiter.try_acquire(tokens=1)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed < 0.01  # Should return immediately

    def test_reset_refills_to_capacity(self):
        """Test that reset refills bucket to full capacity."""
        limiter = RateLimiter(rate=10.0, capacity=20.0)

        # Consume tokens
        limiter.acquire(tokens=15, blocking=False)
        assert limiter.tokens == 5.0

        # Reset
        limiter.reset()
        assert limiter.tokens == 20.0

    def test_rate_limiter_thread_safe(self):
        """Test that rate limiter is thread-safe."""
        import threading

        limiter = RateLimiter(rate=100.0, capacity=100.0)
        results = []

        def acquire_tokens():
            for _ in range(10):
                results.append(limiter.acquire(tokens=1, blocking=True, timeout=1.0))

        # Create multiple threads
        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # All acquisitions should succeed (50 tokens requested, 100 available)
        assert all(results)
        assert len(results) == 50


class TestRateLimitConfig:
    """Test suite for rate limit configuration."""

    def test_default_rates(self):
        """Test default rate limit values."""
        assert RateLimitConfig.DEFAULT_S3_RATE == 100.0
        assert RateLimitConfig.DEFAULT_GDRIVE_RATE == 10.0
        assert RateLimitConfig.DEFAULT_DROPBOX_RATE == 5.0

    @patch.dict('os.environ', {}, clear=True)
    def test_config_from_env_defaults(self):
        """Test loading config with default values."""
        config = RateLimitConfig.from_env()

        assert config['enabled'] is True
        assert config['s3'] == 100.0
        assert config['gdrive'] == 10.0
        assert config['dropbox'] == 5.0

    @patch.dict('os.environ', {
        'RATE_LIMIT_S3': '50',
        'RATE_LIMIT_GDRIVE': '5',
        'RATE_LIMIT_DROPBOX': '2'
    })
    def test_config_from_env_custom_values(self):
        """Test loading config with custom environment variables."""
        config = RateLimitConfig.from_env()

        assert config['s3'] == 50.0
        assert config['gdrive'] == 5.0
        assert config['dropbox'] == 2.0

    @patch.dict('os.environ', {'RATE_LIMIT_ENABLED': 'false'})
    def test_config_disabled(self):
        """Test disabling rate limiting via environment variable."""
        config = RateLimitConfig.from_env()

        assert config['enabled'] is False
        assert config['s3'] is None
        assert config['gdrive'] is None
        assert config['dropbox'] is None


class TestS3ConnectorRateLimiting:
    """Test suite for S3 connector rate limiting integration."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(rate=2.0, capacity=2.0)  # 2 req/sec

    @pytest.fixture
    def s3_connector(self, rate_limiter):
        """Create S3 connector with rate limiter."""
        connector = S3Connector(
            bucket_name="test-bucket",
            rate_limiter=rate_limiter
        )
        connector._connected = True  # Mock connection
        return connector

    def test_s3_connector_accepts_rate_limiter(self, rate_limiter):
        """Test that S3 connector accepts rate limiter parameter."""
        connector = S3Connector(
            bucket_name="test-bucket",
            rate_limiter=rate_limiter
        )
        assert connector._rate_limiter is rate_limiter

    def test_upload_file_checks_rate_limit(self, s3_connector, rate_limiter, tmp_path):
        """Test that upload_file checks rate limit."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Consume all tokens
        rate_limiter.acquire(tokens=2, blocking=False)

        # Upload should fail due to rate limit
        result = s3_connector.upload_file(test_file, "test.txt")
        assert result['success'] is False
        assert 'rate limit' in result['error'].lower()

    def test_download_file_checks_rate_limit(self, s3_connector, rate_limiter, tmp_path):
        """Test that download_file checks rate limit."""
        # Consume all tokens
        rate_limiter.acquire(tokens=2, blocking=False)

        # Download should fail due to rate limit
        result = s3_connector.download_file("test.txt", tmp_path / "output.txt")
        assert result['success'] is False
        assert 'rate limit' in result['error'].lower()

    def test_delete_file_checks_rate_limit(self, s3_connector, rate_limiter):
        """Test that delete_file checks rate limit."""
        # Consume all tokens
        rate_limiter.acquire(tokens=2, blocking=False)

        # Delete should fail due to rate limit
        result = s3_connector.delete_file("test.txt")
        assert result['success'] is False
        assert 'rate limit' in result['error'].lower()

    def test_list_files_checks_rate_limit(self, s3_connector, rate_limiter):
        """Test that list_files checks rate limit."""
        # Consume all tokens
        rate_limiter.acquire(tokens=2, blocking=False)

        # List should return empty due to rate limit
        result = s3_connector.list_files()
        assert result == []

    def test_multiple_operations_consume_tokens(self, s3_connector, rate_limiter, tmp_path):
        """Test that multiple operations consume tokens correctly."""
        # Start with 2 tokens
        assert rate_limiter.get_available_tokens() == 2.0

        # Mock the S3 client
        s3_connector.s3_client = Mock()
        s3_connector.s3_client.head_object.return_value = {
            'Metadata': {},
            'ContentLength': 100
        }

        # First operation (download) - consumes 1 token
        test_file = tmp_path / "test.txt"
        s3_connector.download_file("test.txt", test_file)
        assert rate_limiter.get_available_tokens() < 2.0

        # Second operation (delete) - consumes 1 token
        s3_connector.delete_file("test.txt")
        assert rate_limiter.get_available_tokens() < 1.0

    def test_operations_without_rate_limiter(self, tmp_path):
        """Test that operations work without rate limiter."""
        connector = S3Connector(bucket_name="test-bucket")  # No rate limiter
        connector._connected = True
        connector.s3_client = Mock()
        connector.s3_client.head_object.return_value = {
            'Metadata': {},
            'ContentLength': 100
        }

        # Operations should succeed without rate limiting
        result = connector.download_file("test.txt", tmp_path / "output.txt")
        # Will fail due to mock, but not due to rate limiting
        assert 'rate limit' not in str(result.get('error', '')).lower()

    def test_rate_limit_logging(self, s3_connector, rate_limiter, caplog):
        """Test that rate limit warnings are logged."""
        import logging
        caplog.set_level(logging.WARNING)

        # Consume all tokens
        rate_limiter.acquire(tokens=2, blocking=False)

        # Try list operation (should hit rate limit)
        s3_connector.list_files()

        # Check for rate limit log message
        assert any('rate limit' in msg.lower() for msg in caplog.messages)
