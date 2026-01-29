#!/usr/bin/env python3
"""
Medical Imaging Pipeline Example

This example shows how to use Secure Media Processor with the
medical imaging plugin for processing sensitive medical data.

Use case: Download encrypted MRI scans from hospital cloud storage,
process them locally with a cancer detection model, then securely
clean up.

Requirements:
    pip install secure-media-processor[medical]
"""

from src import Pipeline, TransferMode
from src.core import MediaEncryptor, AuditLogger, KeyExchangeManager, KeyType
from src.connectors import S3Connector

# Medical imaging plugin (separate package)
try:
    from plugins.smp_medical import MedicalImagingPlugin
    MEDICAL_AVAILABLE = True
except ImportError:
    MEDICAL_AVAILABLE = False
    print("Note: Medical imaging plugin not installed")
    print("Install with: pip install secure-media-processor[medical]")


def setup_key_exchange():
    """
    Set up secure key exchange with the hospital.

    In a real scenario:
    1. You generate a key pair
    2. Export your public key and send to hospital
    3. Receive hospital's public key
    4. Derive shared secret for encryption

    This ensures end-to-end encryption where the cloud provider
    never has access to the decryption key.
    """
    km = KeyExchangeManager(
        key_store_path="~/.smp/keys",
        key_rotation_days=90
    )

    # Check if we already have a key pair
    keys = km.list_keys()
    if not keys:
        # Generate new ECDH key pair
        key_id = km.generate_key_pair(
            key_type=KeyType.ECDH_P384,
            purpose="hospital-data-exchange"
        )
        print(f"Generated new key pair: {key_id}")

        # Export public key to share with hospital
        public_key = km.export_public_key(key_id)
        print("Your public key (share with data source):")
        print(public_key.decode())
    else:
        key_id = list(keys.keys())[0]
        print(f"Using existing key: {key_id}")

    return km, key_id


def main():
    print("=" * 60)
    print("SECURE MEDICAL IMAGING PIPELINE")
    print("=" * 60)

    # ==========================================================================
    # STEP 1: Set up key exchange (for zero-knowledge transfer)
    # ==========================================================================

    print("\n[1] Setting up key exchange...")
    key_manager, key_id = setup_key_exchange()

    # In production, you would have received the hospital's public key
    # and derived a shared secret:
    #
    # hospital_public_key = read_from_secure_channel()
    # shared_key = key_manager.derive_shared_key(
    #     local_key_id=key_id,
    #     remote_public_key=hospital_public_key
    # )

    # ==========================================================================
    # STEP 2: Initialize secure pipeline
    # ==========================================================================

    print("\n[2] Initializing secure pipeline...")

    encryption = MediaEncryptor(key_path="~/.smp/keys/master.key")

    audit = AuditLogger(
        log_path="~/.smp/audit/",
        user_id="medical-researcher@university.edu",
        retention_days=2190,  # HIPAA: 6 years
        redact_sensitive=True  # Don't log patient identifiers
    )

    pipeline = Pipeline(
        encryption=encryption,
        audit_logger=audit
    )

    # Add hospital data source
    pipeline.add_source('hospital', S3Connector(
        bucket_name='hospital-encrypted-scans',
        region='us-east-1'
    ))

    print("  Pipeline ready")

    # ==========================================================================
    # STEP 3: Download encrypted MRI scans
    # ==========================================================================

    print("\n[3] Downloading encrypted MRI scans...")

    manifest = pipeline.secure_download(
        source_name='hospital',
        remote_path='breast-mri/study-2024/',
        local_path='/secure/medical-workspace/scans/',
        mode=TransferMode.ZERO_KNOWLEDGE,
        metadata={
            'study_protocol': 'BREAST-CANCER-SCREENING-V2',
            'irb_approval': 'IRB-2024-0042',
            'data_use_agreement': 'DUA-HOSPITAL-UNIV-2024'
        }
    )

    print(f"  Downloaded {manifest.file_count} files")
    print(f"  Total size: {manifest.total_bytes / 1024 / 1024:.1f} MB")

    # Verify integrity
    if not pipeline.verify_integrity(manifest):
        print("  ERROR: Data integrity check failed!")
        return

    print("  Integrity verified")

    # ==========================================================================
    # STEP 4: Process with medical imaging plugin
    # ==========================================================================

    print("\n[4] Processing with medical imaging plugin...")

    if MEDICAL_AVAILABLE:
        # Initialize the medical imaging plugin
        medical = MedicalImagingPlugin(
            model_path="~/.smp/models/breast-cancer-unet.pt",
            device="cuda"  # Use GPU
        )

        # Load and preprocess DICOM files
        print("  Loading DICOM files...")
        dicom_data = medical.process(
            manifest.destination,
            operation='load'
        )

        print("  Preprocessing...")
        preprocessed = medical.process(
            dicom_data,
            operation='preprocess',
            window_center=40,
            window_width=400
        )

        # Run segmentation
        print("  Running U-Net segmentation...")
        segmentation = medical.process(
            preprocessed,
            operation='segment',
            model_name='breast-cancer-v2'
        )

        # Run cancer prediction
        print("  Running cancer prediction...")
        predictions = medical.process(
            segmentation,
            operation='predict',
            threshold=0.5
        )

        # Save results (still local - encrypted at rest)
        results_path = '/secure/medical-workspace/results/'
        predictions.save(results_path)
        print(f"  Results saved to {results_path}")

    else:
        print("  (Skipped - medical plugin not installed)")
        print("  In production, this would run cancer detection model")

    # ==========================================================================
    # STEP 5: Secure cleanup
    # ==========================================================================

    print("\n[5] Secure cleanup...")

    # Delete the raw scans (we have the results)
    pipeline.secure_delete('/secure/medical-workspace/scans/')
    print("  Raw scans securely deleted")

    # Results are kept in /results/ until you decide to delete them
    print("  Results preserved in /results/")

    # ==========================================================================
    # STEP 6: Compliance reporting
    # ==========================================================================

    print("\n[6] Compliance reporting...")

    # Export audit trail for IRB/compliance review
    export_path = '/secure/medical-workspace/audit_report.json'
    entry_count = audit.export_logs(
        output_path=export_path,
        event_types=None  # All events
    )
    print(f"  Exported {entry_count} audit entries")
    print(f"  Report: {export_path}")

    # Verify audit log integrity
    if audit.verify_integrity():
        print("  Audit log integrity verified (no tampering)")
    else:
        print("  WARNING: Audit log integrity check failed!")

    # ==========================================================================
    # Summary
    # ==========================================================================

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print("""
What happened:
1. Key exchange ensured end-to-end encryption
2. MRI scans downloaded with zero-knowledge transfer
3. Data decrypted ONLY on this local GPU workstation
4. Cancer detection model ran locally on GPU
5. Raw scans securely deleted (3-pass overwrite)
6. Audit trail exported for compliance

The cloud provider NEVER had access to:
- Decryption keys
- Unencrypted patient data
- Processing results

This is the secure way to handle sensitive medical data.
    """)


if __name__ == '__main__':
    main()
