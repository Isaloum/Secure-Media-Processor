HIPAA Compliance Guide
======================

Secure Media Processor is designed to help organizations meet HIPAA security
requirements for handling Protected Health Information (PHI).

HIPAA Security Rule Requirements
--------------------------------

Access Controls (§164.312(a))
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirement**: Implement technical policies to allow only authorized access.

**SMP Implementation**:

* Key-based authentication for all transfers
* Role-based access through connector credentials
* Audit logging of all access attempts

.. code-block:: python

   # All access is authenticated and logged
   logger.log_event(
       event_type=AuditEventType.DATA_ACCESS,
       description="Accessed patient study",
       user_id="dr.smith",
       resource_id="STUDY-001"
   )

Audit Controls (§164.312(b))
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirement**: Implement hardware, software, and procedural mechanisms to record
and examine access.

**SMP Implementation**:

* Hash-chained audit logs (tamper-evident)
* Comprehensive event logging
* Compliance export functionality

.. code-block:: python

   from src.core import AuditLogger, AuditEventType

   logger = AuditLogger(log_path="/secure/audit")

   # All events are logged with hash chain
   logger.log_event(
       event_type=AuditEventType.FILE_DOWNLOAD,
       description="Downloaded mammogram study",
       user_id="dr.jones",
       resource_id="MAMMO-2024-001",
       metadata={"ip_address": "192.168.1.100"}
   )

   # Export for compliance audit
   logger.export_for_compliance("hipaa_audit_q1_2024.json")

Integrity (§164.312(c))
~~~~~~~~~~~~~~~~~~~~~~~

**Requirement**: Implement policies to protect PHI from improper alteration or destruction.

**SMP Implementation**:

* AES-256-GCM authenticated encryption
* Checksum verification on all transfers
* Hash chain for audit logs

.. code-block:: python

   # Checksum verification prevents tampering
   result = connector.download_file(
       remote_path="study.zip",
       local_path="/tmp/study.zip",
       verify_checksum=True  # Fails if data modified
   )

Transmission Security (§164.312(e))
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Requirement**: Implement technical security measures to guard against unauthorized
access during transmission.

**SMP Implementation**:

* ECDH key exchange for secure channels
* End-to-end encryption
* TLS for all cloud API calls

.. code-block:: python

   from src.core import KeyExchange, SecureTransferPipeline, TransferMode

   # Establish secure channel
   kex = KeyExchange()
   shared_key = kex.derive_shared_key(my_private, partner_public)

   # Zero-knowledge transfer (maximum privacy)
   pipeline = SecureTransferPipeline()
   result = pipeline.secure_download(
       remote_path="s3://bucket/phi_data.zip",
       local_path="/secure/data.zip",
       mode=TransferMode.ZERO_KNOWLEDGE
   )

PHI Anonymization
-----------------

Safe Harbor Method
~~~~~~~~~~~~~~~~~~

Remove all 18 HIPAA identifiers:

.. code-block:: python

   from src.medical import MedicalPipeline

   pipeline = MedicalPipeline()

   # Anonymize DICOM files
   result = pipeline.anonymize_study(
       input_path="/raw/study/",
       output_path="/anonymized/study/",
       method="safe_harbor",
       retain_dates=False,
       retain_institution=False
   )

   print(f"Removed identifiers from {result['files_processed']} files")

Secure Disposal
---------------

NIST SP 800-88 / DoD 5220.22-M
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.core import SecureTransferPipeline

   pipeline = SecureTransferPipeline()

   # DoD-compliant secure deletion
   result = pipeline.secure_delete(
       file_path="/tmp/phi_study.zip",
       passes=3  # 3-pass overwrite
   )

   # Log the deletion
   logger.log_event(
       event_type=AuditEventType.FILE_DELETE,
       description="Secure deletion of PHI",
       resource_id="PHI-STUDY-001"
   )

Compliance Checklist
--------------------

.. list-table:: HIPAA Technical Safeguards Checklist
   :header-rows: 1
   :widths: 40 40 20

   * - Requirement
     - SMP Feature
     - Status
   * - Access Control (§164.312(a))
     - Key-based authentication
     - ✓
   * - Audit Controls (§164.312(b))
     - Hash-chained audit logs
     - ✓
   * - Integrity (§164.312(c))
     - AES-256-GCM + checksums
     - ✓
   * - Person Authentication (§164.312(d))
     - ECDH key exchange
     - ✓
   * - Transmission Security (§164.312(e))
     - End-to-end encryption
     - ✓

Business Associate Agreements
-----------------------------

When using cloud storage providers (AWS, Azure, Google Cloud), ensure you have
a signed Business Associate Agreement (BAA) with each provider before storing PHI.

For More Information
--------------------

* `HHS HIPAA Security Rule <https://www.hhs.gov/hipaa/for-professionals/security/index.html>`_
* `NIST HIPAA Security Toolkit <https://www.nist.gov/programs-projects/security-health-information-technology>`_
