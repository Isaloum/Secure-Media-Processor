"""
Encryption Lambda Function
Handles file encryption and decryption
"""
import json
import os
import sys
import base64
from datetime import datetime

# Add shared layer to path
sys.path.insert(0, "/opt/python")

import boto3
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from db_utils import execute_query
from response import (
    success_response,
    error_response,
    validation_error,
    not_found_error,
)

s3_client = boto3.client("s3")
MEDIA_BUCKET = os.environ["MEDIA_BUCKET"]


def lambda_handler(event, context):
    """Main Lambda handler for encryption endpoints"""
    try:
        # Parse request
        method = event.get("httpMethod")
        path = event.get("path", "")
        body = json.loads(event.get("body", "{}"))

        # Get user from JWT
        user_id = extract_user_id(event)
        if not user_id:
            return error_response("Unauthorized", 401)

        # Route to appropriate handler
        if "/encrypt" in path:
            return handle_encrypt(body, user_id)
        elif "/decrypt" in path:
            return handle_decrypt(body, user_id)
        else:
            return error_response("Unknown endpoint", 404)

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response("Internal server error", 500)


def extract_user_id(event):
    """Extract user ID from JWT token (simplified)"""
    # TODO: Implement proper JWT validation
    return "mock-user-id-123"


def handle_encrypt(body, user_id):
    """Encrypt a file"""
    file_id = body.get("file_id")
    password = body.get("password")

    if not file_id or not password:
        return validation_error("file_id and password are required")

    # Fetch file metadata
    files = execute_query(
        "SELECT s3_key, original_filename FROM files WHERE id = %s AND user_id = %s",
        (file_id, user_id)
    )

    if not files:
        return not_found_error("File not found")

    file_data = files[0]

    # Download file from S3
    try:
        response = s3_client.get_object(
            Bucket=MEDIA_BUCKET,
            Key=file_data["s3_key"]
        )
        plaintext = response["Body"].read()
    except Exception as e:
        return error_response(f"Failed to download file: {str(e)}", 500)

    # Encrypt file
    encrypted_data, salt, iv = encrypt_data(plaintext, password)

    # Upload encrypted file back to S3
    encrypted_key = f"{file_data['s3_key']}.encrypted"
    try:
        s3_client.put_object(
            Bucket=MEDIA_BUCKET,
            Key=encrypted_key,
            Body=encrypted_data,
            Metadata={
                "salt": base64.b64encode(salt).decode(),
                "iv": base64.b64encode(iv).decode(),
                "encryption_algorithm": "AES-256-CBC"
            }
        )
    except Exception as e:
        return error_response(f"Failed to upload encrypted file: {str(e)}", 500)

    # Update database
    execute_query(
        """
        UPDATE files
        SET encryption_algorithm = %s, s3_key = %s
        WHERE id = %s
        """,
        ("AES-256-CBC", encrypted_key, file_id),
        fetch=False
    )

    return success_response({
        "file_id": file_id,
        "message": "File encrypted successfully",
        "algorithm": "AES-256-CBC"
    })


def handle_decrypt(body, user_id):
    """Decrypt a file"""
    file_id = body.get("file_id")
    password = body.get("password")

    if not file_id or not password:
        return validation_error("file_id and password are required")

    # Fetch file metadata
    files = execute_query(
        "SELECT s3_key, encryption_algorithm FROM files WHERE id = %s AND user_id = %s",
        (file_id, user_id)
    )

    if not files:
        return not_found_error("File not found")

    file_data = files[0]

    if not file_data["encryption_algorithm"]:
        return error_response("File is not encrypted", 400)

    # Download encrypted file from S3
    try:
        response = s3_client.get_object(
            Bucket=MEDIA_BUCKET,
            Key=file_data["s3_key"]
        )
        encrypted_data = response["Body"].read()
        metadata = response["Metadata"]

        salt = base64.b64decode(metadata["salt"])
        iv = base64.b64decode(metadata["iv"])
    except Exception as e:
        return error_response(f"Failed to download file: {str(e)}", 500)

    # Decrypt file
    try:
        plaintext = decrypt_data(encrypted_data, password, salt, iv)
    except Exception as e:
        return error_response(f"Decryption failed: {str(e)}", 400)

    # Generate presigned URL for decrypted file (temporary)
    decrypted_key = file_data["s3_key"].replace(".encrypted", ".decrypted")
    s3_client.put_object(
        Bucket=MEDIA_BUCKET,
        Key=decrypted_key,
        Body=plaintext
    )

    download_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": MEDIA_BUCKET,
            "Key": decrypted_key
        },
        ExpiresIn=3600  # 1 hour
    )

    return success_response({
        "file_id": file_id,
        "download_url": download_url,
        "expires_in": 3600,
        "message": "File decrypted successfully"
    })


def encrypt_data(plaintext, password):
    """Encrypt data using AES-256-CBC"""
    # Generate salt and derive key
    salt = os.urandom(16)
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())

    # Generate IV
    iv = os.urandom(16)

    # Encrypt
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # Pad plaintext to AES block size (16 bytes)
    padding_length = 16 - (len(plaintext) % 16)
    padded_plaintext = plaintext + bytes([padding_length] * padding_length)

    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

    return ciphertext, salt, iv


def decrypt_data(ciphertext, password, salt, iv):
    """Decrypt data using AES-256-CBC"""
    # Derive key
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())

    # Decrypt
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()

    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove padding
    padding_length = padded_plaintext[-1]
    plaintext = padded_plaintext[:-padding_length]

    return plaintext
