Core Modules
============

The core modules provide the fundamental security primitives for secure data transfer.

SecureTransferPipeline
----------------------

.. automodule:: src.core.secure_transfer
   :members:
   :undoc-members:
   :show-inheritance:

KeyExchange
-----------

The KeyExchange module provides ECDH key exchange for establishing secure channels
between multiple parties.

.. automodule:: src.core.key_exchange
   :members:
   :undoc-members:
   :show-inheritance:

AuditLogger
-----------

HIPAA-compliant audit logging with hash chain verification.

.. automodule:: src.core.audit_logger
   :members:
   :undoc-members:
   :show-inheritance:

Enums and Types
---------------

TransferMode
~~~~~~~~~~~~

.. autoclass:: src.core.secure_transfer.TransferMode
   :members:
   :undoc-members:

AuditEventType
~~~~~~~~~~~~~~

.. autoclass:: src.core.audit_logger.AuditEventType
   :members:
   :undoc-members:

Examples
--------

Key Exchange Between Two Parties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.core import KeyExchange

   # Initialize
   kex = KeyExchange()

   # Party A generates their keypair
   priv_a, pub_a = kex.generate_ecdh_keypair()

   # Party B generates their keypair
   priv_b, pub_b = kex.generate_ecdh_keypair()

   # Both parties derive the same shared secret
   shared_a = kex.derive_shared_key(priv_a, pub_b)
   shared_b = kex.derive_shared_key(priv_b, pub_a)

   assert shared_a == shared_b  # True!

Secure File Transfer
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.core import SecureTransferPipeline, TransferMode

   pipeline = SecureTransferPipeline()

   # Download with encryption
   result = pipeline.secure_download(
       remote_path="s3://medical-data/study001.zip",
       local_path="/secure/study001.zip",
       mode=TransferMode.ZERO_KNOWLEDGE
   )

   # Process the data...

   # Secure deletion (DoD 5220.22-M compliant)
   pipeline.secure_delete("/secure/study001.zip", passes=3)

HIPAA-Compliant Audit Logging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.core import AuditLogger, AuditEventType

   logger = AuditLogger(log_path="./audit_logs")

   # Log events
   logger.log_event(
       event_type=AuditEventType.FILE_DOWNLOAD,
       description="Downloaded patient study",
       user_id="dr.smith",
       resource_id="STUDY-001"
   )

   # Verify chain integrity
   assert logger.verify_chain() is True

   # Export for compliance audit
   logger.export_for_compliance("./compliance_report.json")
