"""
Key Exchange Module

Provides secure key exchange mechanisms for multi-party data transfers.

Features:
- RSA key pair generation and management
- ECDH (Elliptic Curve Diffie-Hellman) key exchange
- Key derivation functions (HKDF, PBKDF2)
- Key wrapping for secure key storage
- Hardware Security Module (HSM) integration hooks

Security Model:
- Private keys never leave the local workstation
- Key exchange allows secure communication with hospitals/data sources
- Derived keys are used for individual transfer sessions
- Keys are rotated periodically for forward secrecy
"""

import os
import hashlib
import hmac
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """Supported key types."""
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    ECDH_P256 = "ecdh_p256"
    ECDH_P384 = "ecdh_p384"
    ECDH_P521 = "ecdh_p521"


@dataclass
class KeyPair:
    """Represents a cryptographic key pair."""
    key_id: str
    key_type: KeyType
    created_at: datetime
    expires_at: Optional[datetime]
    public_key_pem: bytes
    private_key_encrypted: bytes  # Always stored encrypted
    metadata: Dict[str, Any]


@dataclass
class DerivedKey:
    """A session key derived from key exchange."""
    key_id: str
    derived_from: str  # Parent key ID
    purpose: str  # e.g., "encryption", "authentication"
    key_material: bytes  # The actual key (keep in memory only)
    created_at: datetime
    expires_at: datetime


class KeyExchangeManager:
    """
    Manages cryptographic keys and key exchange operations.

    This class handles:
    - Generation of RSA and ECDH key pairs
    - Secure storage of private keys (encrypted at rest)
    - Key exchange protocols for multi-party transfers
    - Session key derivation

    Example:
        # Initialize key manager
        km = KeyExchangeManager(key_store_path="~/.smp/keys")

        # Generate a key pair for your workstation
        key_id = km.generate_key_pair(KeyType.ECDH_P384)

        # Export public key to share with data source (e.g., hospital)
        public_key = km.export_public_key(key_id)

        # Receive their public key and derive shared secret
        shared_key = km.derive_shared_key(
            local_key_id=key_id,
            remote_public_key=hospital_public_key
        )

        # Use shared key for secure transfer
        encrypted_data = km.encrypt_with_key(shared_key, data)
    """

    def __init__(
        self,
        key_store_path: str,
        master_password: Optional[str] = None,
        key_rotation_days: int = 90,
        hsm_provider: Optional[Any] = None
    ):
        """
        Initialize the key exchange manager.

        Args:
            key_store_path: Directory for encrypted key storage
            master_password: Password for encrypting stored keys
            key_rotation_days: Days before keys should be rotated
            hsm_provider: Optional HSM provider for hardware key storage
        """
        self._key_store_path = Path(key_store_path).expanduser()
        self._key_rotation_days = key_rotation_days
        self._hsm = hsm_provider
        self._keys: Dict[str, KeyPair] = {}
        self._session_keys: Dict[str, DerivedKey] = {}

        # Create key store with restricted permissions
        self._key_store_path.mkdir(parents=True, exist_ok=True)
        os.chmod(self._key_store_path, 0o700)

        # Derive master key from password
        if master_password:
            self._master_key = self._derive_master_key(master_password)
        else:
            # Generate and store a random master key
            self._master_key = self._load_or_create_master_key()

        # Load existing keys
        self._load_keys()

    def generate_key_pair(
        self,
        key_type: KeyType = KeyType.ECDH_P384,
        purpose: str = "transfer",
        expires_days: Optional[int] = None
    ) -> str:
        """
        Generate a new key pair.

        Args:
            key_type: Type of key to generate
            purpose: Description of key purpose
            expires_days: Days until key expires (None = never)

        Returns:
            Key ID for the generated key pair
        """
        key_id = self._generate_key_id()
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expires_days) if expires_days else None

        # Generate the key pair
        if key_type in (KeyType.RSA_2048, KeyType.RSA_4096):
            private_key, public_key = self._generate_rsa_key(key_type)
        else:
            private_key, public_key = self._generate_ecdh_key(key_type)

        # Serialize public key
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Encrypt and serialize private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_encrypted = self._encrypt_key_material(private_key_pem)

        # Create key pair record
        key_pair = KeyPair(
            key_id=key_id,
            key_type=key_type,
            created_at=created_at,
            expires_at=expires_at,
            public_key_pem=public_key_pem,
            private_key_encrypted=private_key_encrypted,
            metadata={"purpose": purpose}
        )

        # Store key
        self._keys[key_id] = key_pair
        self._save_key(key_pair)

        logger.info(f"Generated {key_type.value} key pair: {key_id}")
        return key_id

    def export_public_key(self, key_id: str) -> bytes:
        """
        Export the public key for sharing with remote parties.

        Args:
            key_id: ID of the key pair

        Returns:
            PEM-encoded public key
        """
        if key_id not in self._keys:
            raise KeyError(f"Key not found: {key_id}")

        return self._keys[key_id].public_key_pem

    def import_public_key(self, public_key_pem: bytes, key_id: Optional[str] = None) -> str:
        """
        Import a remote party's public key.

        Args:
            public_key_pem: PEM-encoded public key
            key_id: Optional ID to assign (auto-generated if not provided)

        Returns:
            Key ID for the imported key
        """
        key_id = key_id or self._generate_key_id()

        # Validate the public key
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        load_pem_public_key(public_key_pem, backend=default_backend())

        # Store as a key pair with no private key
        key_pair = KeyPair(
            key_id=key_id,
            key_type=KeyType.ECDH_P384,  # Default, will be detected on use
            created_at=datetime.utcnow(),
            expires_at=None,
            public_key_pem=public_key_pem,
            private_key_encrypted=b"",  # No private key for imported keys
            metadata={"imported": True}
        )

        self._keys[key_id] = key_pair
        logger.info(f"Imported public key: {key_id}")
        return key_id

    def derive_shared_key(
        self,
        local_key_id: str,
        remote_public_key: bytes,
        purpose: str = "encryption",
        key_length: int = 32
    ) -> DerivedKey:
        """
        Derive a shared secret using ECDH key exchange.

        This creates a symmetric key that both parties can derive
        independently, allowing secure communication.

        Args:
            local_key_id: ID of your private key
            remote_public_key: Remote party's public key (PEM)
            purpose: Purpose of the derived key
            key_length: Length of derived key in bytes

        Returns:
            DerivedKey with the shared secret
        """
        if local_key_id not in self._keys:
            raise KeyError(f"Key not found: {local_key_id}")

        key_pair = self._keys[local_key_id]

        # Load our private key
        private_key_pem = self._decrypt_key_material(key_pair.private_key_encrypted)
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )

        # Load their public key
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        remote_key = load_pem_public_key(remote_public_key, backend=default_backend())

        # Perform ECDH key exchange
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            shared_secret = private_key.exchange(ec.ECDH(), remote_key)
        else:
            raise ValueError("Key exchange requires an ECDH key")

        # Derive the actual key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA384(),
            length=key_length,
            salt=None,
            info=purpose.encode(),
            backend=default_backend()
        ).derive(shared_secret)

        # Create derived key record
        session_key_id = self._generate_key_id()
        derived = DerivedKey(
            key_id=session_key_id,
            derived_from=local_key_id,
            purpose=purpose,
            key_material=derived_key,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)  # Session keys expire in 24h
        )

        self._session_keys[session_key_id] = derived
        logger.info(f"Derived shared key: {session_key_id}")
        return derived

    def encrypt_with_key(self, derived_key: DerivedKey, plaintext: bytes) -> bytes:
        """
        Encrypt data with a derived session key.

        Args:
            derived_key: Session key from key exchange
            plaintext: Data to encrypt

        Returns:
            Encrypted data (nonce + ciphertext)
        """
        if datetime.utcnow() > derived_key.expires_at:
            raise ValueError("Session key has expired")

        nonce = os.urandom(12)
        cipher = AESGCM(derived_key.key_material)
        ciphertext = cipher.encrypt(nonce, plaintext, None)

        return nonce + ciphertext

    def decrypt_with_key(self, derived_key: DerivedKey, ciphertext: bytes) -> bytes:
        """
        Decrypt data with a derived session key.

        Args:
            derived_key: Session key from key exchange
            ciphertext: Data to decrypt (nonce + ciphertext)

        Returns:
            Decrypted plaintext
        """
        if datetime.utcnow() > derived_key.expires_at:
            raise ValueError("Session key has expired")

        nonce = ciphertext[:12]
        actual_ciphertext = ciphertext[12:]

        cipher = AESGCM(derived_key.key_material)
        return cipher.decrypt(nonce, actual_ciphertext, None)

    def rotate_key(self, old_key_id: str) -> str:
        """
        Rotate a key by generating a new one and marking old as expired.

        Args:
            old_key_id: ID of key to rotate

        Returns:
            New key ID
        """
        if old_key_id not in self._keys:
            raise KeyError(f"Key not found: {old_key_id}")

        old_key = self._keys[old_key_id]

        # Generate new key of same type
        new_key_id = self.generate_key_pair(
            key_type=old_key.key_type,
            purpose=old_key.metadata.get("purpose", "transfer"),
            expires_days=self._key_rotation_days
        )

        # Mark old key as expired
        old_key.expires_at = datetime.utcnow()
        self._save_key(old_key)

        logger.info(f"Rotated key {old_key_id} -> {new_key_id}")
        return new_key_id

    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all keys with their metadata."""
        result = {}
        for key_id, key_pair in self._keys.items():
            result[key_id] = {
                "key_type": key_pair.key_type.value,
                "created_at": key_pair.created_at.isoformat(),
                "expires_at": key_pair.expires_at.isoformat() if key_pair.expires_at else None,
                "has_private_key": bool(key_pair.private_key_encrypted),
                "metadata": key_pair.metadata
            }
        return result

    def check_key_expiration(self) -> Dict[str, bool]:
        """Check which keys are expired or expiring soon."""
        result = {}
        now = datetime.utcnow()
        warning_threshold = now + timedelta(days=30)

        for key_id, key_pair in self._keys.items():
            if key_pair.expires_at:
                if key_pair.expires_at < now:
                    result[key_id] = "expired"
                elif key_pair.expires_at < warning_threshold:
                    result[key_id] = "expiring_soon"
                else:
                    result[key_id] = "valid"
            else:
                result[key_id] = "no_expiration"

        return result

    def destroy_key(self, key_id: str) -> None:
        """
        Securely destroy a key.

        Args:
            key_id: ID of key to destroy
        """
        if key_id in self._keys:
            # Overwrite key material before deletion
            key_pair = self._keys[key_id]
            key_file = self._key_store_path / f"{key_id}.key"

            if key_file.exists():
                # Secure delete
                file_size = key_file.stat().st_size
                with open(key_file, 'r+b') as f:
                    for _ in range(3):
                        f.seek(0)
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())
                key_file.unlink()

            del self._keys[key_id]
            logger.info(f"Destroyed key: {key_id}")

    # Private methods

    def _generate_key_id(self) -> str:
        """Generate a unique key ID."""
        import uuid
        return str(uuid.uuid4())[:12]

    def _derive_master_key(self, password: str) -> bytes:
        """Derive master key from password using PBKDF2."""
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def _get_or_create_salt(self) -> bytes:
        """Get or create the salt for master key derivation."""
        salt_file = self._key_store_path / ".salt"
        if salt_file.exists():
            return salt_file.read_bytes()
        else:
            salt = os.urandom(32)
            salt_file.write_bytes(salt)
            os.chmod(salt_file, 0o600)
            return salt

    def _load_or_create_master_key(self) -> bytes:
        """Load or create a random master key."""
        master_file = self._key_store_path / ".master"
        if master_file.exists():
            return master_file.read_bytes()
        else:
            master_key = os.urandom(32)
            master_file.write_bytes(master_key)
            os.chmod(master_file, 0o600)
            return master_key

    def _encrypt_key_material(self, key_material: bytes) -> bytes:
        """Encrypt key material for storage."""
        nonce = os.urandom(12)
        cipher = AESGCM(self._master_key)
        ciphertext = cipher.encrypt(nonce, key_material, None)
        return nonce + ciphertext

    def _decrypt_key_material(self, encrypted: bytes) -> bytes:
        """Decrypt stored key material."""
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        cipher = AESGCM(self._master_key)
        return cipher.decrypt(nonce, ciphertext, None)

    def _generate_rsa_key(self, key_type: KeyType) -> Tuple[Any, Any]:
        """Generate an RSA key pair."""
        key_size = 4096 if key_type == KeyType.RSA_4096 else 2048
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        return private_key, private_key.public_key()

    def _generate_ecdh_key(self, key_type: KeyType) -> Tuple[Any, Any]:
        """Generate an ECDH key pair."""
        curve_map = {
            KeyType.ECDH_P256: ec.SECP256R1(),
            KeyType.ECDH_P384: ec.SECP384R1(),
            KeyType.ECDH_P521: ec.SECP521R1()
        }
        curve = curve_map.get(key_type, ec.SECP384R1())
        private_key = ec.generate_private_key(curve, default_backend())
        return private_key, private_key.public_key()

    def _save_key(self, key_pair: KeyPair) -> None:
        """Save a key pair to disk."""
        import json
        key_file = self._key_store_path / f"{key_pair.key_id}.key"

        data = {
            "key_id": key_pair.key_id,
            "key_type": key_pair.key_type.value,
            "created_at": key_pair.created_at.isoformat(),
            "expires_at": key_pair.expires_at.isoformat() if key_pair.expires_at else None,
            "public_key_pem": key_pair.public_key_pem.decode(),
            "private_key_encrypted": key_pair.private_key_encrypted.hex(),
            "metadata": key_pair.metadata
        }

        key_file.write_text(json.dumps(data, indent=2))
        os.chmod(key_file, 0o600)

    def _load_keys(self) -> None:
        """Load all keys from disk."""
        import json

        for key_file in self._key_store_path.glob("*.key"):
            try:
                data = json.loads(key_file.read_text())

                key_pair = KeyPair(
                    key_id=data["key_id"],
                    key_type=KeyType(data["key_type"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
                    public_key_pem=data["public_key_pem"].encode(),
                    private_key_encrypted=bytes.fromhex(data["private_key_encrypted"]),
                    metadata=data.get("metadata", {})
                )

                self._keys[key_pair.key_id] = key_pair
            except Exception as e:
                logger.error(f"Failed to load key from {key_file}: {e}")
