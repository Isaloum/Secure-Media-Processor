#!/usr/bin/env python3
"""
Basic Secure Transfer Example

This example demonstrates the core functionality of Secure Media Processor:
- Setting up a secure transfer pipeline
- Downloading encrypted data from cloud
- Processing locally on GPU
- Secure cleanup

This is the primary use case: getting sensitive data safely to your
local GPU workstation for processing.
"""

from src import Pipeline, TransferMode
from src.core import MediaEncryptor, AuditLogger
from src.connectors import S3Connector

def main():
    # ==========================================================================
    # STEP 1: Initialize the secure pipeline
    # ==========================================================================

    # Set up encryption (uses AES-256-GCM)
    encryption = MediaEncryptor(
        key_path="~/.smp/keys/master.key"  # Will create if doesn't exist
    )

    # Set up audit logging (for HIPAA/GDPR compliance)
    audit = AuditLogger(
        log_path="~/.smp/audit/",
        user_id="researcher@example.org",
        retention_days=2190  # 6 years for HIPAA
    )

    # Create the pipeline
    pipeline = Pipeline(
        encryption=encryption,
        audit_logger=audit,
        verify_checksums=True,
        secure_delete_passes=3  # DoD 5220.22-M style deletion
    )

    print("Pipeline initialized")

    # ==========================================================================
    # STEP 2: Add cloud data sources
    # ==========================================================================

    # Add AWS S3 source (where sensitive data is stored)
    pipeline.add_source('hospital-data', S3Connector(
        bucket_name='patient-scans-encrypted',
        region='us-east-1'
        # Credentials from AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY env vars
        # or ~/.aws/credentials
    ))

    print("Cloud source added: hospital-data")

    # ==========================================================================
    # STEP 3: Secure download to local GPU workstation
    # ==========================================================================

    # Progress callback to show download status
    def show_progress(transferred: int, total: int):
        if total > 0:
            pct = (transferred / total) * 100
            bar_len = 40
            filled = int(bar_len * transferred / total)
            bar = '=' * filled + '-' * (bar_len - filled)
            print(f"\r[{bar}] {pct:.1f}%", end="", flush=True)

    print("\nStarting secure download...")

    # Download with ZERO_KNOWLEDGE mode
    # In this mode, data was encrypted at the source (hospital)
    # and we decrypt it locally - the cloud provider never sees plaintext
    manifest = pipeline.secure_download(
        source_name='hospital-data',
        remote_path='mri-scans/patient-001/',
        local_path='/secure/gpu-workspace/input/',
        mode=TransferMode.ZERO_KNOWLEDGE,
        progress_callback=show_progress,
        metadata={
            'study_id': 'RESEARCH-2024-001',
            'purpose': 'breast-cancer-analysis',
            'approved_by': 'IRB-12345'
        }
    )

    print(f"\n\nDownload complete!")
    print(f"  Transfer ID: {manifest.transfer_id}")
    print(f"  Files: {manifest.file_count}")
    print(f"  Bytes: {manifest.total_bytes:,}")
    print(f"  Destination: {manifest.destination}")

    # ==========================================================================
    # STEP 4: Verify data integrity
    # ==========================================================================

    print("\nVerifying integrity...")

    if pipeline.verify_integrity(manifest):
        print("  Checksums verified - data is intact")
    else:
        print("  WARNING: Checksum mismatch detected!")
        # In production, you might want to re-download or alert

    # ==========================================================================
    # STEP 5: Process data locally (YOUR CODE HERE)
    # ==========================================================================

    print("\nProcessing data on local GPU...")

    # The data is now at manifest.destination as regular files
    # You can use any tool to process it:
    #
    # - PyTorch/TensorFlow models
    # - OpenCV
    # - DICOM tools (pydicom)
    # - Your custom code
    #
    # Example:
    #   import your_model
    #   results = your_model.process(manifest.destination)
    #   results.save('/secure/gpu-workspace/output/')

    # For this example, we'll just simulate processing
    import time
    time.sleep(2)  # Simulate GPU processing
    print("  Processing complete")

    # ==========================================================================
    # STEP 6: Secure cleanup
    # ==========================================================================

    print("\nSecure cleanup...")

    # Securely delete the input data
    # This overwrites the files multiple times before deletion
    # so the sensitive data cannot be recovered from disk
    pipeline.secure_delete('/secure/gpu-workspace/input/')
    print("  Input data securely deleted")

    # Note: Results in /output/ are kept for your use
    # Delete them when you're done with secure_delete as well

    # ==========================================================================
    # STEP 7: View audit log
    # ==========================================================================

    print("\nAudit trail:")
    print(f"  Log entries: {audit.get_entry_count()}")
    print(f"  Log location: ~/.smp/audit/")
    print("  Run 'audit.export_logs(\"report.json\")' to export for compliance")

    print("\nDone!")


if __name__ == '__main__':
    main()
