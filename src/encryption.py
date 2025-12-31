import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class EncryptionService:
    def __init__(self, password: str):
        self.password = password.encode()
        self.salt = os.urandom(16)
        self.key = self._derive_key()

    def _derive_key(self) -> bytes:
        kdf = Scrypt(
            salt=self.salt,
            length=32,
            n=2**14,
            r=8,
            p=1,
        )
        return kdf.derive(self.password)

    def encrypt(self, data: bytes) -> bytes:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(iv))
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        return self.salt + iv + encrypted_data

    def decrypt(self, encrypted_data: bytes) -> bytes:
        self.salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        self.key = self._derive_key()
        cipher = Cipher(algorithms.AES(self.key), modes.CFB(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data[32:]) + decryptor.finalize()
