#!/usr/bin/env python3
"""Example: Multi-cloud storage with Secure Media Processor.

This example demonstrates:
1. Encrypting a file before upload
2. Uploading to multiple cloud providers
3. Using ConnectorManager for multi-cloud sync
4. Downloading and verifying integrity

Note: This example requires cloud credentials to be configured.
See docs/api/cloud.md for setup instructions.
"""

from pathlib import Path
import tempfile
import os

from src.core.encryption import MediaEncryptor


def check_credentials():
    """Check if cloud credentials are available."""
    has_s3 = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
    has_drive = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    has_dropbox = bool(os.environ.get("DROPBOX_ACCESS_TOKEN"))

    print("=== Credential Check ===")
    print(f"AWS S3: {'✓ Configured' if has_s3 else '✗ Not configured'}")
    print(f"Google Drive: {'✓ Configured' if has_drive else '✗ Not configured'}")
    print(f"Dropbox: {'✓ Configured' if has_dropbox else '✗ Not configured'}")
    print()

    return has_s3, has_drive, has_dropbox


def example_s3_upload():
    """Demonstrate S3 upload/download."""
    from src.cloud.connectors import S3Connector

    print("=== S3 Upload Example ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create and encrypt a file
        input_file = tmpdir / "data.txt"
        input_file.write_text("Important data for cloud backup")

        encrypted_file = tmpdir / "data.enc"
        encryptor = MediaEncryptor(str(tmpdir / "key"))
        encryptor.encrypt_file(str(input_file), str(encrypted_file))
        print(f"Encrypted file: {encrypted_file}")

        # Upload to S3
        bucket = os.environ.get("AWS_BUCKET_NAME", "my-secure-bucket")
        s3 = S3Connector(bucket_name=bucket)

        result = s3.upload_file(
            str(encrypted_file),
            "backups/example/data.enc"
        )

        if result["success"]:
            print(f"✓ Uploaded to: s3://{bucket}/{result['remote_key']}")
            print(f"  Size: {result['size']:,} bytes")
            print(f"  Checksum: {result['checksum'][:16]}...")
        else:
            print(f"✗ Upload failed: {result.get('error')}")
            return

        # Download and verify
        download_path = tmpdir / "downloaded.enc"
        result = s3.download_file(
            "backups/example/data.enc",
            str(download_path),
            verify_checksum=True
        )

        if result["success"]:
            print(f"✓ Downloaded to: {download_path}")
            print(f"  Checksum verified: {result['checksum_verified']}")

        # Decrypt and verify content
        restored_file = tmpdir / "restored.txt"
        encryptor.decrypt_file(str(download_path), str(restored_file))

        original = input_file.read_text()
        restored = restored_file.read_text()
        print(f"\n✓ Content integrity verified: {original == restored}")

        # List files in bucket
        print("\nFiles in backups/example/:")
        for f in s3.list_files(prefix="backups/example/"):
            print(f"  {f['key']}: {f['size']} bytes")

        # Cleanup
        s3.delete_file("backups/example/data.enc")
        print("\n✓ Cleaned up remote file")


def example_multi_cloud_sync():
    """Demonstrate multi-cloud sync with ConnectorManager."""
    from src.cloud.connectors import ConnectorManager, S3Connector

    print("\n=== Multi-Cloud Sync Example ===\n")

    # Create manager
    manager = ConnectorManager()

    # Register available connectors
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        bucket = os.environ.get("AWS_BUCKET_NAME", "my-bucket")
        manager.register_connector("s3", S3Connector(bucket_name=bucket))
        print("Registered: S3")

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        from src.cloud.connectors import GoogleDriveConnector
        manager.register_connector("drive", GoogleDriveConnector())
        print("Registered: Google Drive")

    if os.environ.get("DROPBOX_ACCESS_TOKEN"):
        from src.cloud.connectors import DropboxConnector
        manager.register_connector("dropbox", DropboxConnector())
        print("Registered: Dropbox")

    if not manager.connectors:
        print("No cloud providers configured. Skipping sync example.")
        return

    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create encrypted file
        input_file = tmpdir / "critical_backup.enc"
        input_file.write_bytes(os.urandom(1024))  # Random data

        # Sync to all clouds at once
        print("Syncing to all configured clouds...")
        results = manager.sync_file(
            str(input_file),
            "multi-cloud-example/critical_backup.enc"
        )

        print("\nSync Results:")
        for provider, result in results.items():
            status = "✓" if result.get("success") else "✗"
            print(f"  {status} {provider}: {result.get('remote_key', result.get('error'))}")


def main():
    """Run cloud storage examples."""
    has_s3, has_drive, has_dropbox = check_credentials()

    if not any([has_s3, has_drive, has_dropbox]):
        print("No cloud credentials configured.")
        print("\nTo run this example, set environment variables:")
        print("  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME")
        print("  GOOGLE_APPLICATION_CREDENTIALS")
        print("  DROPBOX_ACCESS_TOKEN")
        print("\nSee docs/api/cloud.md for details.")
        return

    if has_s3:
        try:
            example_s3_upload()
        except Exception as e:
            print(f"S3 example failed: {e}")

    try:
        example_multi_cloud_sync()
    except Exception as e:
        print(f"Multi-cloud example failed: {e}")


if __name__ == "__main__":
    main()
