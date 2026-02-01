Security Model
==============

Secure Media Processor implements defense-in-depth security for protecting sensitive
data throughout its lifecycle.

Encryption
----------

End-to-End Encryption
~~~~~~~~~~~~~~~~~~~~~

All data is encrypted using **AES-256-GCM** (Galois/Counter Mode):

* 256-bit key strength
* Authenticated encryption (prevents tampering)
* Unique IV/nonce per encryption operation
* Constant-time comparison to prevent timing attacks

.. code-block:: python

   from src.core import SecureTransferPipeline

   pipeline = SecureTransferPipeline()

   # Data is encrypted at rest and in transit
   result = pipeline.secure_download(
       remote_path="s3://bucket/sensitive.zip",
       local_path="/tmp/data.zip"
   )

Key Exchange
~~~~~~~~~~~~

**ECDH (Elliptic Curve Diffie-Hellman)** is used for secure key exchange:

* P-384 curve for strong security
* Forward secrecy (compromised long-term keys don't expose past sessions)
* No key transmission required (only public keys exchanged)

.. code-block:: python

   from src.core import KeyExchange

   kex = KeyExchange()

   # Generate keypair
   private, public = kex.generate_ecdh_keypair()

   # Derive shared secret with partner's public key
   shared = kex.derive_shared_key(private, partner_public_key)

Secure Deletion
---------------

DoD 5220.22-M Compliance
~~~~~~~~~~~~~~~~~~~~~~~~

Secure deletion follows the US Department of Defense standard:

1. **Pass 1**: Overwrite with zeros (0x00)
2. **Pass 2**: Overwrite with ones (0xFF)
3. **Pass 3**: Overwrite with random data

.. code-block:: python

   pipeline.secure_delete("/path/to/file", passes=3)

This ensures data cannot be recovered even with forensic tools.

Audit Logging
-------------

Hash Chain Verification
~~~~~~~~~~~~~~~~~~~~~~~

All audit logs are cryptographically linked using a hash chain:

* Each log entry contains the hash of the previous entry
* Any tampering breaks the chain and is detected
* Provides non-repudiation for compliance audits

.. code-block:: python

   from src.core import AuditLogger

   logger = AuditLogger()

   # Log events
   logger.log_event(...)

   # Verify chain integrity
   is_valid = logger.verify_chain()

Sensitive Data Redaction
~~~~~~~~~~~~~~~~~~~~~~~~

The audit logger automatically redacts sensitive data patterns:

* Social Security Numbers
* Credit card numbers
* Email addresses (configurable)
* Custom patterns

Memory Security
---------------

Credential Cleanup
~~~~~~~~~~~~~~~~~~

All credentials are securely cleared from memory when no longer needed:

* Connectors clear credentials on disconnect
* ``__del__`` methods zero out sensitive strings
* No credential caching beyond session

Path Validation
~~~~~~~~~~~~~~~

All file paths are validated to prevent traversal attacks:

.. code-block:: python

   # This is automatically blocked:
   connector.download_file("../../../etc/passwd", "/tmp/file")
   # Raises: ValueError: Invalid path: directory traversal detected

Rate Limiting
~~~~~~~~~~~~~

Built-in rate limiting prevents API abuse:

.. code-block:: python

   from src.connectors import S3Connector, RateLimiter

   limiter = RateLimiter(max_requests=100, window_seconds=60)
   connector = S3Connector(bucket_name="...", rate_limiter=limiter)

Security Recommendations
------------------------

1. **Use Zero-Knowledge Mode** for maximum privacy
2. **Enable audit logging** for all operations
3. **Implement key rotation** every 90 days
4. **Use hardware security modules** for production key storage
5. **Run in Docker** with minimal privileges
6. **Keep dependencies updated** for security patches
