# Security Model

## Overview

Secure Media Processor (SMP) is designed with a **zero-trust security model** where sensitive data is protected at every stage of the transfer pipeline. The core principle is simple: **data is encrypted before leaving the source and decrypted only on the local GPU workstation**.

## Threat Model

### Assets to Protect

1. **Sensitive Data** - Medical images, patient records, confidential documents
2. **Encryption Keys** - Must never be exposed to cloud providers or transit
3. **Audit Logs** - Must be tamper-proof for compliance
4. **Processing Results** - May contain sensitive derived information

### Adversaries

| Adversary | Capability | Mitigation |
|-----------|------------|------------|
| Cloud Provider | Access to stored data, metadata | End-to-end encryption; provider never sees plaintext |
| Network Attacker | Man-in-the-middle, traffic analysis | TLS + application-layer encryption; metadata minimization |
| Malicious Insider | Access to cloud credentials | Zero-knowledge mode; audit logging |
| Forensic Recovery | Disk/memory analysis | Secure deletion; memory encryption |

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TRUSTED ZONE                                      │
│                    (Local GPU Workstation)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Decryption happens here                                           │   │
│  │ • Keys stored here (encrypted at rest)                              │   │
│  │ • Processing happens here                                           │   │
│  │ • Audit logs stored here                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          ══════════╪══════════  ENCRYPTION BOUNDARY
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNTRUSTED ZONE                                      │
│                    (Cloud / Network / Transit)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Only encrypted data passes through                                │   │
│  │ • No access to keys                                                 │   │
│  │ • Metadata minimized                                                │   │
│  │ • Cannot decrypt or modify data                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Encryption Architecture

### Algorithms

| Purpose | Algorithm | Key Size | Notes |
|---------|-----------|----------|-------|
| Data Encryption | AES-256-GCM | 256-bit | Authenticated encryption |
| Key Exchange | ECDH (P-384) | 384-bit | Forward secrecy |
| Key Derivation | HKDF-SHA384 | N/A | Derives session keys |
| Key Storage | AES-256-GCM | 256-bit | Master key encryption |
| Integrity | SHA-256 | 256-bit | File checksums |
| Audit Log Chain | SHA-256 | 256-bit | Hash chain for integrity |

### Key Hierarchy

```
Master Password (optional)
         │
         ▼
    ┌─────────┐
    │ PBKDF2  │  480,000 iterations
    └────┬────┘
         │
         ▼
    Master Key ──────────────────────────┐
         │                               │
         ▼                               ▼
    ┌─────────────┐              ┌─────────────┐
    │ Key Pair 1  │              │ Key Pair N  │
    │ (Identity)  │              │ (Per-party) │
    └──────┬──────┘              └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ Session Key │  ECDH + HKDF
    │ (Per-xfer)  │  24-hour expiry
    └─────────────┘
```

### Encryption Workflow

1. **Key Generation**
   - Generate ECDH key pair on local workstation
   - Private key encrypted with master key, stored locally
   - Public key exported to share with data sources

2. **Key Exchange**
   - Receive remote party's public key (e.g., hospital)
   - Perform ECDH to derive shared secret
   - Apply HKDF to derive session encryption key

3. **Data Encryption**
   - Generate random 96-bit nonce per file
   - Encrypt with AES-256-GCM using session key
   - Prepend nonce to ciphertext
   - Calculate SHA-256 checksum

4. **Transfer**
   - Upload encrypted blob to cloud
   - Cloud provider sees only encrypted bytes
   - TLS provides transport security (defense in depth)

5. **Decryption**
   - Download encrypted blob
   - Verify checksum
   - Decrypt using session key
   - Verify GCM authentication tag

## Data Flow Security

### Standard Transfer Mode

```
┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│ Data Source  │      │    Cloud    │      │ GPU Station  │
│ (Hospital)   │      │  (S3/GCS)   │      │   (Local)    │
└──────┬───────┘      └──────┬──────┘      └──────┬───────┘
       │                     │                    │
       │  1. Encrypt locally │                    │
       │◄────────────────────│                    │
       │                     │                    │
       │  2. Upload encrypted│                    │
       │────────────────────►│                    │
       │                     │                    │
       │                     │  3. Download       │
       │                     │────────────────────►
       │                     │                    │
       │                     │  4. Verify checksum│
       │                     │                    ▼
       │                     │  5. Decrypt locally│
       │                     │                    ▼
       │                     │  6. Process on GPU │
       │                     │                    ▼
       │                     │  7. Secure delete  │
       │                     │                    │
```

### Zero-Knowledge Mode

In zero-knowledge mode, data is encrypted **at the source** before SMP ever sees it:

```
┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│ Data Source  │      │    Cloud    │      │ GPU Station  │
│ (Hospital)   │      │  (S3/GCS)   │      │   (Local)    │
└──────┬───────┘      └──────┬──────┘      └──────┬───────┘
       │                     │                    │
       │  1. Source encrypts │                    │
       │     with shared key │                    │
       ├─────────────────────►                    │
       │                     │                    │
       │  2. Cloud stores    │                    │
       │     encrypted blob  │                    │
       │                     │  3. Download       │
       │                     │────────────────────►
       │                     │                    │
       │                     │  4. Decrypt with   │
       │                     │     shared key     │
       │                     │                    ▼
       │                     │                    │

Neither SMP nor Cloud ever sees plaintext in this mode.
The shared key is derived via ECDH - never transmitted.
```

## Secure Storage

### Key Storage

Private keys are stored encrypted:

```
~/.smp/keys/
├── .master          # Master key (protected by password or random)
├── .salt            # PBKDF2 salt (32 bytes)
├── abc123def.key    # Key pair (encrypted JSON)
└── xyz789ghi.key    # Key pair (encrypted JSON)

File permissions: 0600 (owner read/write only)
Directory permissions: 0700 (owner only)
```

### Temporary Files

During transfer:
- Temp files created in `~/.smp/temp/`
- Permissions: 0600
- Secure deletion after use (3-pass overwrite)

### Audit Logs

```
~/.smp/audit/
├── audit_2024-01-15.jsonl
├── audit_2024-01-16.jsonl
└── audit_2024-01-17.jsonl

Each entry contains:
- Cryptographic hash chain (tamper detection)
- No sensitive data (paths redacted)
- Timestamps in UTC
```

## Secure Deletion

SMP implements DoD 5220.22-M style secure deletion:

1. **Pass 1**: Overwrite with zeros (0x00)
2. **Pass 2**: Overwrite with ones (0xFF)
3. **Pass 3**: Overwrite with random data
4. **Sync**: Force write to disk (fsync)
5. **Delete**: Remove file

This applies to:
- Temporary files during transfer
- Decrypted data after processing (optional)
- Expired session keys

## Compliance Considerations

### HIPAA

| Requirement | SMP Implementation |
|-------------|-------------------|
| Access controls | Local-only decryption, no cloud access to plaintext |
| Audit controls | Immutable audit log with hash chain |
| Transmission security | End-to-end encryption + TLS |
| Encryption | AES-256-GCM (NIST approved) |

### GDPR

| Requirement | SMP Implementation |
|-------------|-------------------|
| Data minimization | Only transfer what's needed |
| Encryption | State of the art (AES-256-GCM) |
| Right to erasure | Secure deletion feature |
| Audit trail | Complete transfer history |

## Security Recommendations

### For Users

1. **Use a strong master password** - Protects your keys at rest
2. **Enable zero-knowledge mode** - For maximum security
3. **Rotate keys regularly** - Default 90 days
4. **Run secure deletion** - After processing sensitive data
5. **Review audit logs** - Detect unauthorized access

### For Deployment

1. **Isolate the GPU workstation** - Network segmentation
2. **Full disk encryption** - Protect data at rest
3. **Physical security** - Control access to hardware
4. **Regular updates** - Keep SMP and dependencies current
5. **Backup audit logs** - Offsite, encrypted

## Known Limitations

1. **Memory encryption** - Not yet implemented; data is plaintext in GPU memory during processing
2. **Side-channel attacks** - Standard mitigations, not resistant to sophisticated hardware attacks
3. **Key backup** - User responsibility; lost master password = lost access
4. **Metadata** - File sizes visible to cloud provider; use padding if sensitive

## Security Contact

Report security vulnerabilities to: security@example.com

See [SECURITY.md](../../SECURITY.md) for responsible disclosure policy.
