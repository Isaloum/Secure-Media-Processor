#!/usr/bin/env python3
"""
Secure Media Processor - Quick Demo (Non-Interactive)
======================================================

A quick demonstration of the core features without user interaction.
Perfect for CI/CD testing or quick showcases.

Run with: python demo/quick_demo.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("Secure Media Processor - Quick Demo")
    print("=" * 60)
    print()

    success_count = 0
    total_tests = 5

    # Test 1: Core imports
    print("[1/5] Testing core module imports...")
    try:
        from src.core import SecureTransferPipeline, AuditLogger, KeyExchange
        print("  ✓ Core modules imported successfully")
        success_count += 1
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")

    # Test 2: Key Exchange
    print("\n[2/5] Testing ECDH key exchange...")
    try:
        from src.core import KeyExchange
        kex = KeyExchange()

        priv_a, pub_a = kex.generate_ecdh_keypair()
        priv_b, pub_b = kex.generate_ecdh_keypair()

        shared_a = kex.derive_shared_key(priv_a, pub_b)
        shared_b = kex.derive_shared_key(priv_b, pub_a)

        if shared_a == shared_b:
            print("  ✓ Key exchange successful - shared secrets match")
            success_count += 1
        else:
            print("  ✗ Key exchange failed - secrets don't match")
    except Exception as e:
        print(f"  ✗ Key exchange failed: {e}")

    # Test 3: Audit Logger
    print("\n[3/5] Testing audit logger with hash chain...")
    try:
        from src.core import AuditLogger, AuditEventType

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = AuditLogger(log_path=temp_dir)

            # Log some events
            for i in range(3):
                logger.log_event(
                    event_type=AuditEventType.DATA_ACCESS,
                    description=f"Test event {i+1}",
                    user_id="demo_user"
                )

            # Verify chain
            if logger.verify_chain():
                print("  ✓ Audit logger working - hash chain verified")
                success_count += 1
            else:
                print("  ✗ Hash chain verification failed")
    except Exception as e:
        print(f"  ✗ Audit logger failed: {e}")

    # Test 4: Connectors
    print("\n[4/5] Testing cloud connectors availability...")
    try:
        from src.connectors import (
            S3Connector,
            GoogleDriveConnector,
            DropboxConnector,
            AZURE_AVAILABLE
        )

        connectors = ["S3", "GoogleDrive", "Dropbox"]
        if AZURE_AVAILABLE:
            from src.connectors import AzureBlobConnector
            connectors.append("Azure")

        print(f"  ✓ Available connectors: {', '.join(connectors)}")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Connector import failed: {e}")

    # Test 5: Medical Pipeline (optional)
    print("\n[5/5] Testing medical pipeline (optional)...")
    try:
        from src.medical import MedicalPipeline
        print("  ✓ Medical pipeline available")
        success_count += 1
    except ImportError:
        print("  ○ Medical pipeline not installed (install with [medical] extra)")
        success_count += 1  # Not a failure, just optional

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{total_tests} tests passed")
    print("=" * 60)

    if success_count == total_tests:
        print("\n✓ All tests passed! Secure Media Processor is ready to use.")
        return 0
    else:
        print(f"\n✗ {total_tests - success_count} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
