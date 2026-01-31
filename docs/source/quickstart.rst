Quickstart Guide
================

This guide will help you get started with Secure Media Processor in just a few minutes.

1. Install the Package
----------------------

.. code-block:: bash

   pip install secure-media-processor[all]

2. Basic Secure Transfer
------------------------

.. code-block:: python

   from src.core import SecureTransferPipeline, AuditLogger, AuditEventType
   from src.connectors import S3Connector

   # Initialize components
   pipeline = SecureTransferPipeline()
   logger = AuditLogger(log_path="./audit")

   # Connect to cloud storage
   connector = S3Connector(
       bucket_name="my-bucket",
       region="us-east-1"
   )
   connector.connect()

   # Download file securely
   result = connector.download_file(
       remote_path="data/sensitive.zip",
       local_path="/tmp/sensitive.zip",
       verify_checksum=True
   )

   # Log the event
   logger.log_event(
       event_type=AuditEventType.FILE_DOWNLOAD,
       description="Downloaded sensitive data",
       user_id="demo_user"
   )

   # Process your data here...

   # Secure deletion when done
   pipeline.secure_delete("/tmp/sensitive.zip")

   logger.log_event(
       event_type=AuditEventType.FILE_DELETE,
       description="Securely deleted data",
       user_id="demo_user"
   )

   connector.disconnect()

3. Secure Key Exchange
----------------------

When transferring data between two parties:

.. code-block:: python

   from src.core import KeyExchange

   kex = KeyExchange()

   # Each party generates their keypair
   my_private, my_public = kex.generate_ecdh_keypair()

   # Exchange public keys (send my_public to partner)
   # Receive partner's public key

   partner_public = "..."  # Received from partner

   # Derive shared secret
   shared_key = kex.derive_shared_key(my_private, partner_public)

   # Both parties now have the same shared_key for encryption

4. Using the CLI
----------------

.. code-block:: bash

   # Show help
   smp --help

   # Download securely
   smp secure-download s3://bucket/file.zip /local/file.zip

   # Process medical study
   smp process-study s3://bucket/study/ --study-id STUDY-001

   # Secure delete
   smp secure-delete /path/to/sensitive/file --passes 3

   # Export audit logs
   smp audit-export --output compliance_report.json

5. Medical Imaging Workflow
---------------------------

.. code-block:: python

   from src.medical import MedicalPipeline

   pipeline = MedicalPipeline()

   result = pipeline.process_study(
       remote_path="s3://hospital/studies/CT-001/",
       operations=["load", "anonymize", "preprocess", "predict"],
       study_id="CT-001"
   )

   print(f"Diagnosis: {result.prediction}")
   print(f"Confidence: {result.confidence:.2%}")

Next Steps
----------

* Read the :doc:`api/core` documentation
* Explore :doc:`cloud-connectors` for multi-cloud support
* Learn about :doc:`hipaa-compliance` for healthcare applications
