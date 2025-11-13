"""
Cryptographic utilities for Secure Credential Transfer
Implements AES-GCM encryption/decryption as per RFC 5116
"""

import os
import base64
import json
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class EncryptionError(Exception):
    """Custom exception for encryption errors"""
    pass


class DecryptionError(Exception):
    """Custom exception for decryption errors"""
    pass


def generate_secret(key_length: int = 128) -> str:
    """
    Generate a random secret for encryption

    Args:
        key_length: Key length in bits (128 or 256)

    Returns:
        Base64-encoded secret
    """
    if key_length not in [128, 256]:
        raise ValueError("key_length must be 128 or 256")

    key_bytes = key_length // 8
    secret = os.urandom(key_bytes)
    return base64.b64encode(secret).decode('utf-8')


def encrypt_provisioning_info(
    provisioning_info: Dict,
    secret: str,
    algorithm: str = "AEAD_AES_128_GCM"
) -> Dict:
    """
    Encrypt provisioning information using AES-GCM

    Args:
        provisioning_info: Dictionary containing provisioning information
        secret: Base64-encoded encryption key
        algorithm: Encryption algorithm (AEAD_AES_128_GCM or AEAD_AES_256_GCM)

    Returns:
        Dictionary with encrypted payload structure:
        {
            "type": "AEAD_AES_128_GCM",
            "data": "base64(iv + ciphertext + tag)"
        }
    """
    try:
        # Decode secret
        key = base64.b64decode(secret)

        # Validate key length
        if algorithm == "AEAD_AES_128_GCM" and len(key) != 16:
            raise EncryptionError("Secret must be 128 bits (16 bytes) for AEAD_AES_128_GCM")
        elif algorithm == "AEAD_AES_256_GCM" and len(key) != 32:
            raise EncryptionError("Secret must be 256 bits (32 bytes) for AEAD_AES_256_GCM")

        # Initialize AES-GCM
        aesgcm = AESGCM(key)

        # Generate random 96-bit (12-byte) IV
        iv = os.urandom(12)

        # Convert provisioning info to JSON bytes
        plaintext = json.dumps(provisioning_info).encode('utf-8')

        # Encrypt (this produces ciphertext + 128-bit tag)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)

        # Combine IV + ciphertext + tag
        encrypted_data = iv + ciphertext_with_tag

        # Base64 encode
        encoded_data = base64.b64encode(encrypted_data).decode('utf-8')

        return {
            "type": algorithm,
            "data": encoded_data
        }

    except Exception as e:
        raise EncryptionError(f"Encryption failed: {str(e)}")


def decrypt_provisioning_info(
    encrypted_payload: Dict,
    secret: str
) -> Dict:
    """
    Decrypt provisioning information using AES-GCM

    Args:
        encrypted_payload: Dictionary with structure:
            {
                "type": "AEAD_AES_128_GCM",
                "data": "base64(iv + ciphertext + tag)"
            }
        secret: Base64-encoded encryption key

    Returns:
        Dictionary containing decrypted provisioning information
    """
    try:
        # Validate payload structure
        if not isinstance(encrypted_payload, dict):
            raise DecryptionError("Encrypted payload must be a dictionary")

        if 'type' not in encrypted_payload or 'data' not in encrypted_payload:
            raise DecryptionError("Encrypted payload must contain 'type' and 'data' fields")

        algorithm = encrypted_payload['type']
        encoded_data = encrypted_payload['data']

        # Decode secret
        key = base64.b64decode(secret)

        # Validate key length
        if algorithm == "AEAD_AES_128_GCM" and len(key) != 16:
            raise DecryptionError("Secret must be 128 bits (16 bytes) for AEAD_AES_128_GCM")
        elif algorithm == "AEAD_AES_256_GCM" and len(key) != 32:
            raise DecryptionError("Secret must be 256 bits (32 bytes) for AEAD_AES_256_GCM")

        # Decode encrypted data
        encrypted_data = base64.b64decode(encoded_data)

        # Extract IV (first 12 bytes)
        iv = encrypted_data[:12]

        # Extract ciphertext + tag (remaining bytes)
        ciphertext_with_tag = encrypted_data[12:]

        # Initialize AES-GCM
        aesgcm = AESGCM(key)

        # Decrypt
        plaintext = aesgcm.decrypt(iv, ciphertext_with_tag, None)

        # Parse JSON
        provisioning_info = json.loads(plaintext.decode('utf-8'))

        return provisioning_info

    except json.JSONDecodeError as e:
        raise DecryptionError(f"Failed to parse decrypted data as JSON: {str(e)}")
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {str(e)}")


def create_encrypted_payload(
    format_type: str,
    content: Dict,
    secret: str,
    algorithm: str = "AEAD_AES_128_GCM"
) -> Dict:
    """
    Create encrypted provisioning information with proper structure

    Args:
        format_type: Provisioning information format (e.g., "digitalwallet.carkey.ccc")
        content: Content dictionary specific to the format
        secret: Base64-encoded encryption key
        algorithm: Encryption algorithm

    Returns:
        Encrypted payload ready for transmission
    """
    provisioning_info = {
        "format": format_type,
        "content": content
    }

    return encrypt_provisioning_info(provisioning_info, secret, algorithm)


def verify_and_decrypt_payload(
    encrypted_payload: Dict,
    secret: str,
    expected_format: str = None
) -> Dict:
    """
    Decrypt and verify provisioning information structure

    Args:
        encrypted_payload: Encrypted payload from relay server
        secret: Base64-encoded encryption key
        expected_format: Optional expected format type for validation

    Returns:
        Decrypted provisioning information
    """
    provisioning_info = decrypt_provisioning_info(encrypted_payload, secret)

    # Validate structure
    if 'format' not in provisioning_info:
        raise DecryptionError("Decrypted payload missing 'format' field")

    if 'content' not in provisioning_info:
        raise DecryptionError("Decrypted payload missing 'content' field")

    # Optionally verify format
    if expected_format and provisioning_info['format'] != expected_format:
        raise DecryptionError(
            f"Format mismatch: expected {expected_format}, got {provisioning_info['format']}"
        )

    return provisioning_info


# Example usage and testing
if __name__ == "__main__":
    # Generate a secret
    secret = generate_secret(128)
    print(f"Generated secret: {secret}")

    # Create sample provisioning information
    sample_content = {
        "credentialId": "12345",
        "issuer": "Example Corp",
        "validUntil": "2024-12-31T23:59:59Z"
    }

    # Encrypt
    encrypted = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=sample_content,
        secret=secret
    )
    print(f"\nEncrypted payload: {json.dumps(encrypted, indent=2)}")

    # Decrypt
    decrypted = verify_and_decrypt_payload(encrypted, secret)
    print(f"\nDecrypted provisioning info: {json.dumps(decrypted, indent=2)}")

    # Verify content matches
    assert decrypted['content'] == sample_content
    print("\n✓ Encryption/Decryption test passed!")
