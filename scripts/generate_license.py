#!/usr/bin/env python3
"""
License key generation script for Secure Media Processor.

Usage:
    python scripts/generate_license.py EMAIL LICENSE_TYPE [DAYS]

Examples:
    python scripts/generate_license.py customer@example.com PRO 365
    python scripts/generate_license.py enterprise@company.com ENTERPRISE 730
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.license_manager import LicenseManager, LicenseType
from datetime import datetime, timedelta


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_license.py EMAIL LICENSE_TYPE [DAYS]")
        print("\nLicense Types: FREE, PRO, ENTERPRISE")
        print("Days: Number of days (omit for lifetime)")
        print("\nExamples:")
        print("  python generate_license.py customer@example.com PRO 365")
        print("  python generate_license.py enterprise@company.com ENTERPRISE")
        sys.exit(1)

    email = sys.argv[1]
    license_type_str = sys.argv[2].upper()
    duration_days = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # Validate license type
    try:
        license_type = LicenseType[license_type_str]
    except KeyError:
        print(f"Error: Invalid license type '{license_type_str}'")
        print("Valid types: FREE, PRO, ENTERPRISE")
        sys.exit(1)

    # Create license manager with production secret
    # TODO: In production, use a secure secret from environment
    manager = LicenseManager(secret_key="PRODUCTION_SECRET_KEY_CHANGE_ME")

    # Generate license
    license = manager.create_license(
        email=email,
        license_type=license_type,
        duration_days=duration_days,
        max_devices=1 if license_type == LicenseType.PRO else 5
    )

    # Display license info
    print("\n" + "="*60)
    print("LICENSE GENERATED SUCCESSFULLY")
    print("="*60)
    print(f"\nLicense Key: {license.license_key}")
    print(f"Email: {license.email}")
    print(f"Type: {license.license_type.value.upper()}")
    print(f"Issued: {license.issued_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if license.expires_at:
        print(f"Expires: {license.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        days_valid = (license.expires_at - license.issued_at).days
        print(f"Valid For: {days_valid} days")
    else:
        print("Expires: Never (Lifetime)")

    print(f"Max Devices: {license.max_devices}")

    print(f"\nEnabled Features:")
    if license.features:
        for feature in license.features:
            print(f"  ✓ {feature.replace('_', ' ').title()}")
    else:
        print("  (None - Free tier)")

    print("\n" + "="*60)
    print("ACTIVATION INSTRUCTIONS")
    print("="*60)
    print("\nSend this to your customer:")
    print(f"\n  License Key: {license.license_key}")
    print(f"\n  To activate:")
    print(f"  1. Install: pip install secure-media-processor")
    print(f"  2. Activate: smp license activate {license.license_key}")
    print(f"  3. Enter your email: {email}")
    print(f"\n  Check status: smp license status")
    print("\n" + "="*60)

    # Save to CSV for record keeping
    csv_file = Path("licenses.csv")
    header_needed = not csv_file.exists()

    with open(csv_file, 'a') as f:
        if header_needed:
            f.write("timestamp,license_key,email,type,duration_days,expires_at\n")

        expires_str = license.expires_at.isoformat() if license.expires_at else "Never"
        f.write(f"{datetime.now().isoformat()},{license.license_key},{email},"
                f"{license.license_type.value},{duration_days or 'Lifetime'},{expires_str}\n")

    print(f"\n✓ License saved to {csv_file}")


if __name__ == "__main__":
    main()
