"""
Rate limiting utilities for cloud connector operations.

Implements token bucket algorithm to prevent API abuse and
excessive costs from cloud provider API calls.
"""

import time
import threading
from typing import Optional


class RateLimiter:
    """Thread-safe token bucket rate limiter.

    The token bucket algorithm allows bursts while maintaining
    an average rate limit over time.
    """

    def __init__(self, rate: float = 10.0, capacity: Optional[float] = None):
        """Initialize rate limiter.

        Args:
            rate: Maximum requests per second (default: 10).
            capacity: Bucket capacity in tokens (default: rate * 2 for burst).
        """
        self.rate = rate  # tokens per second
        self.capacity = capacity or (rate * 2)  # allow 2x burst
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default: 1).
            blocking: Whether to block until tokens are available.
            timeout: Maximum time to wait in seconds (None = wait forever).

        Returns:
            True if tokens were acquired, False otherwise.
        """
        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            with self.lock:
                self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                if not blocking:
                    return False

            # Calculate wait time until next token is available
            wait_time = (tokens - self.tokens) / self.rate

            # Check timeout
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                wait_time = min(wait_time, remaining)

            # Wait for tokens to refill
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens were acquired, False otherwise.
        """
        return self.acquire(tokens, blocking=False)

    def get_available_tokens(self) -> float:
        """Get current number of available tokens.

        Returns:
            Number of tokens currently in the bucket.
        """
        with self.lock:
            self._refill()
            return self.tokens

    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        with self.lock:
            self.tokens = self.capacity
            self.last_refill = time.monotonic()


class RateLimitConfig:
    """Configuration for rate limiting cloud API calls."""

    # Default rates (requests per second)
    DEFAULT_S3_RATE = 100.0  # S3 can handle high throughput
    DEFAULT_GDRIVE_RATE = 10.0  # Drive has stricter limits
    DEFAULT_DROPBOX_RATE = 5.0  # Dropbox is most restrictive

    @classmethod
    def from_env(cls) -> dict:
        """Load rate limit configuration from environment variables.

        Environment variables:
            RATE_LIMIT_S3: S3 rate limit (req/sec)
            RATE_LIMIT_GDRIVE: Google Drive rate limit (req/sec)
            RATE_LIMIT_DROPBOX: Dropbox rate limit (req/sec)
            RATE_LIMIT_ENABLED: Enable/disable rate limiting (default: true)

        Returns:
            Dictionary with rate limiter configurations.
        """
        import os

        enabled = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'

        if not enabled:
            return {
                's3': None,
                'gdrive': None,
                'dropbox': None,
                'enabled': False
            }

        return {
            's3': float(os.getenv('RATE_LIMIT_S3', cls.DEFAULT_S3_RATE)),
            'gdrive': float(os.getenv('RATE_LIMIT_GDRIVE', cls.DEFAULT_GDRIVE_RATE)),
            'dropbox': float(os.getenv('RATE_LIMIT_DROPBOX', cls.DEFAULT_DROPBOX_RATE)),
            'enabled': True
        }
