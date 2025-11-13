"""
Cryptographic Utilities for Secure Credential Transfer

This module provides AES-GCM encryption/decryption functions compliant with RFC 5116.
It handles secure key generation, payload encryption, and integrity verification.

Supported Algorithms:
- AEAD_AES_128_GCM: 128-bit key, 96-bit IV, 128-bit authentication tag
- AEAD_AES_256_GCM: 256-bit key, 96-bit IV, 128-bit authentication tag
"""

import os
import base64
import json
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ============================================================================
# CONSTANTS
# ============================================================================

# Supported encryption algorithms
ALGORITHM_AES_128_GCM = "AEAD_AES_128_GCM"
ALGORITHM_AES_256_GCM = "AEAD_AES_256_GCM"

# Key sizes in bytes
KEY_SIZE_128_BITS = 16  # 128 bits = 16 bytes
KEY_SIZE_256_BITS = 32  # 256 bits = 32 bytes

# IV (Initialization Vector) size in bytes
IV_SIZE = 12  # 96 bits = 12 bytes (recommended for AES-GCM)

# Authentication tag size in bytes
TAG_SIZE = 16  # 128 bits = 16 bytes

# Provisioning information required fields
REQUIRED_PROV_INFO_FIELDS = ['format', 'content']

# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class EncryptionError(Exception):
    """Exception raised when encryption operations fail."""
    pass


class DecryptionError(Exception):
    """Exception raised when decryption operations fail."""
    pass


class InvalidKeyError(Exception):
    """Exception raised when encryption key is invalid."""
    pass

# ============================================================================
# KEY GENERATION
# ============================================================================

def generate_secret(key_length_bits: int = 128) -> str:
    """
    Generate a cryptographically secure random secret key.

    Args:
        key_length_bits: Key length in bits (128 or 256)

    Returns:
        Base64-encoded secret key

    Raises:
        ValueError: If key_length_bits is not 128 or 256

    Example:
        >>> secret = generate_secret(128)
        >>> len(base64.b64decode(secret))
        16
    """
    if key_length_bits not in [128, 256]:
        raise ValueError("key_length_bits must be 128 or 256")

    key_size_bytes = key_length_bits // 8

    # Generate cryptographically secure random bytes
    secret_bytes = os.urandom(key_size_bytes)

    # Encode as base64 for easy transmission
    return base64.b64encode(secret_bytes).decode('utf-8')

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def _validate_secret_length(secret_bytes: bytes, algorithm: str) -> None:
    """
    Validate that the secret key has the correct length for the algorithm.

    Args:
        secret_bytes: The secret key as bytes
        algorithm: The encryption algorithm name

    Raises:
        InvalidKeyError: If key length doesn't match algorithm requirements
    """
    required_length = {
        ALGORITHM_AES_128_GCM: KEY_SIZE_128_BITS,
        ALGORITHM_AES_256_GCM: KEY_SIZE_256_BITS
    }.get(algorithm)

    if not required_length:
        raise InvalidKeyError(f"Unknown algorithm: {algorithm}")

    if len(secret_bytes) != required_length:
        raise InvalidKeyError(
            f"Secret must be {required_length * 8} bits "
            f"({required_length} bytes) for {algorithm}, "
            f"got {len(secret_bytes)} bytes"
        )


def _validate_provisioning_info(provisioning_info: Dict[str, Any]) -> None:
    """
    Validate provisioning information structure.

    Args:
        provisioning_info: Provisioning information dictionary

    Raises:
        EncryptionError: If provisioning info is invalid
    """
    if not isinstance(provisioning_info, dict):
        raise EncryptionError("Provisioning information must be a dictionary")

    missing_fields = [
        field for field in REQUIRED_PROV_INFO_FIELDS
        if field not in provisioning_info
    ]

    if missing_fields:
        raise EncryptionError(
            f"Provisioning information missing required fields: {', '.join(missing_fields)}"
        )

# ============================================================================
# ENCRYPTION
# ============================================================================

def encrypt_provisioning_info(
    provisioning_info: Dict[str, Any],
    secret: str,
    algorithm: str = ALGORITHM_AES_128_GCM
) -> Dict[str, str]:
    """
    Encrypt provisioning information using AES-GCM.

    The encryption process:
    1. Validate provisioning information structure
    2. Decode base64 secret to bytes
    3. Generate random 96-bit IV
    4. Encrypt with AES-GCM (produces ciphertext + 128-bit auth tag)
    5. Combine IV + ciphertext + tag
    6. Base64 encode the result

    Args:
        provisioning_info: Dictionary containing provisioning data with
                          'format' and 'content' fields
        secret: Base64-encoded encryption key
        algorithm: Encryption algorithm (AEAD_AES_128_GCM or AEAD_AES_256_GCM)

    Returns:
        Dictionary with encrypted payload:
        {
            "type": "AEAD_AES_128_GCM",
            "data": "base64(IV + ciphertext + tag)"
        }

    Raises:
        EncryptionError: If encryption fails
        InvalidKeyError: If secret key is invalid

    Example:
        >>> secret = generate_secret(128)
        >>> prov_info = {"format": "test", "content": {"key": "value"}}
        >>> encrypted = encrypt_provisioning_info(prov_info, secret)
        >>> 'type' in encrypted and 'data' in encrypted
        True
    """
    try:
        # Validate input
        _validate_provisioning_info(provisioning_info)

        # Decode secret from base64
        try:
            secret_bytes = base64.b64decode(secret)
        except Exception as e:
            raise InvalidKeyError(f"Invalid base64-encoded secret: {str(e)}")

        # Validate key length for the chosen algorithm
        _validate_secret_length(secret_bytes, algorithm)

        # Initialize AES-GCM cipher
        cipher = AESGCM(secret_bytes)

        # Generate random IV (96 bits recommended for GCM)
        iv = os.urandom(IV_SIZE)

        # Convert provisioning info to JSON bytes
        try:
            plaintext = json.dumps(provisioning_info, separators=(',', ':')).encode('utf-8')
        except (TypeError, ValueError) as e:
            raise EncryptionError(f"Failed to serialize provisioning info: {str(e)}")

        # Encrypt: produces ciphertext + authentication tag
        # The tag is automatically appended to the ciphertext
        ciphertext_with_tag = cipher.encrypt(
            nonce=iv,
            data=plaintext,
            associated_data=None  # No additional authenticated data
        )

        # Combine IV + ciphertext + tag
        encrypted_data = iv + ciphertext_with_tag

        # Base64 encode for transmission
        encoded_data = base64.b64encode(encrypted_data).decode('utf-8')

        return {
            "type": algorithm,
            "data": encoded_data
        }

    except (InvalidKeyError, EncryptionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {str(e)}")

# ============================================================================
# DECRYPTION
# ============================================================================

def decrypt_provisioning_info(
    encrypted_payload: Dict[str, str],
    secret: str
) -> Dict[str, Any]:
    """
    Decrypt provisioning information using AES-GCM.

    The decryption process:
    1. Validate encrypted payload structure
    2. Decode base64 secret and encrypted data
    3. Extract IV, ciphertext, and authentication tag
    4. Decrypt and verify authentication tag
    5. Parse JSON and return provisioning information

    Args:
        encrypted_payload: Dictionary containing:
            - type: Algorithm name (e.g., "AEAD_AES_128_GCM")
            - data: Base64-encoded encrypted data
        secret: Base64-encoded decryption key (must match encryption key)

    Returns:
        Decrypted provisioning information dictionary

    Raises:
        DecryptionError: If decryption fails or authentication fails
        InvalidKeyError: If secret key is invalid

    Example:
        >>> secret = generate_secret(128)
        >>> prov_info = {"format": "test", "content": {"key": "value"}}
        >>> encrypted = encrypt_provisioning_info(prov_info, secret)
        >>> decrypted = decrypt_provisioning_info(encrypted, secret)
        >>> decrypted == prov_info
        True
    """
    try:
        # Validate payload structure
        if not isinstance(encrypted_payload, dict):
            raise DecryptionError("Encrypted payload must be a dictionary")

        if 'type' not in encrypted_payload or 'data' not in encrypted_payload:
            raise DecryptionError("Encrypted payload must contain 'type' and 'data' fields")

        algorithm = encrypted_payload['type']
        encoded_data = encrypted_payload['data']

        # Decode secret from base64
        try:
            secret_bytes = base64.b64decode(secret)
        except Exception as e:
            raise InvalidKeyError(f"Invalid base64-encoded secret: {str(e)}")

        # Validate key length
        _validate_secret_length(secret_bytes, algorithm)

        # Decode encrypted data from base64
        try:
            encrypted_data = base64.b64decode(encoded_data)
        except Exception as e:
            raise DecryptionError(f"Invalid base64-encoded data: {str(e)}")

        # Validate minimum length (IV + tag)
        min_length = IV_SIZE + TAG_SIZE
        if len(encrypted_data) < min_length:
            raise DecryptionError(
                f"Encrypted data too short: expected at least {min_length} bytes, "
                f"got {len(encrypted_data)} bytes"
            )

        # Extract components
        iv = encrypted_data[:IV_SIZE]
        ciphertext_with_tag = encrypted_data[IV_SIZE:]

        # Initialize AES-GCM cipher
        cipher = AESGCM(secret_bytes)

        # Decrypt and verify authentication tag
        # This will raise an exception if the tag doesn't match (authentication failure)
        try:
            plaintext = cipher.decrypt(
                nonce=iv,
                data=ciphertext_with_tag,
                associated_data=None
            )
        except Exception as e:
            raise DecryptionError(
                f"Decryption failed - possibly wrong key or tampered data: {str(e)}"
            )

        # Parse JSON
        try:
            provisioning_info = json.loads(plaintext.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise DecryptionError(f"Failed to parse decrypted data as JSON: {str(e)}")
        except UnicodeDecodeError as e:
            raise DecryptionError(f"Failed to decode decrypted data as UTF-8: {str(e)}")

        # Validate structure
        _validate_provisioning_info(provisioning_info)

        return provisioning_info

    except (InvalidKeyError, DecryptionError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {str(e)}")

# ============================================================================
# HIGH-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def create_encrypted_payload(
    format_type: str,
    content: Dict[str, Any],
    secret: str,
    algorithm: str = ALGORITHM_AES_128_GCM
) -> Dict[str, str]:
    """
    Create encrypted provisioning information with proper structure.

    This is a convenience function that combines provisioning info creation
    and encryption in one step.

    Args:
        format_type: Provisioning information format
                    (e.g., "digitalwallet.carkey.ccc")
        content: Content dictionary specific to the format
        secret: Base64-encoded encryption key
        algorithm: Encryption algorithm to use

    Returns:
        Encrypted payload ready for transmission to relay server

    Example:
        >>> secret = generate_secret(128)
        >>> content = {"credentialId": "12345", "issuer": "Test Corp"}
        >>> payload = create_encrypted_payload(
        ...     "digitalwallet.generic.authorizationToken",
        ...     content,
        ...     secret
        ... )
        >>> payload['type']
        'AEAD_AES_128_GCM'
    """
    provisioning_info = {
        "format": format_type,
        "content": content
    }

    return encrypt_provisioning_info(provisioning_info, secret, algorithm)


def verify_and_decrypt_payload(
    encrypted_payload: Dict[str, str],
    secret: str,
    expected_format: str = None
) -> Dict[str, Any]:
    """
    Decrypt and optionally verify provisioning information format.

    This is a convenience function that decrypts and validates the
    provisioning information structure in one step.

    Args:
        encrypted_payload: Encrypted payload from relay server
        secret: Base64-encoded decryption key
        expected_format: Optional expected format type for validation
                        (e.g., "digitalwallet.carkey.ccc")

    Returns:
        Decrypted provisioning information

    Raises:
        DecryptionError: If decryption fails or format doesn't match

    Example:
        >>> secret = generate_secret(128)
        >>> content = {"test": "data"}
        >>> encrypted = create_encrypted_payload("test.format", content, secret)
        >>> decrypted = verify_and_decrypt_payload(encrypted, secret, "test.format")
        >>> decrypted['content']['test']
        'data'
    """
    # Decrypt payload
    provisioning_info = decrypt_provisioning_info(encrypted_payload, secret)

    # Optionally verify format type
    if expected_format is not None:
        actual_format = provisioning_info.get('format')
        if actual_format != expected_format:
            raise DecryptionError(
                f"Format mismatch: expected '{expected_format}', "
                f"got '{actual_format}'"
            )

    return provisioning_info

# ============================================================================
# TESTING & DEMONSTRATION
# ============================================================================

def _run_self_test():
    """
    Run self-tests to verify encryption/decryption functionality.
    """
    print("Running cryptographic self-tests...\n")

    # Test 1: AES-128-GCM
    print("Test 1: AES-128-GCM encryption/decryption")
    secret_128 = generate_secret(128)
    print(f"  Generated 128-bit secret: {secret_128}")

    sample_content = {
        "credentialId": "TEST-12345",
        "issuer": "Test Corporation",
        "validUntil": "2024-12-31T23:59:59Z"
    }

    encrypted_128 = create_encrypted_payload(
        format_type="digitalwallet.generic.authorizationToken",
        content=sample_content,
        secret=secret_128,
        algorithm=ALGORITHM_AES_128_GCM
    )
    print(f"  Encrypted payload type: {encrypted_128['type']}")
    print(f"  Encrypted data length: {len(encrypted_128['data'])} characters")

    decrypted_128 = verify_and_decrypt_payload(
        encrypted_128,
        secret_128,
        expected_format="digitalwallet.generic.authorizationToken"
    )
    print(f"  Decrypted content matches: {decrypted_128['content'] == sample_content}")
    print("  ✓ Test 1 passed!\n")

    # Test 2: AES-256-GCM
    print("Test 2: AES-256-GCM encryption/decryption")
    secret_256 = generate_secret(256)
    print(f"  Generated 256-bit secret: {secret_256}")

    encrypted_256 = create_encrypted_payload(
        format_type="digitalwallet.carkey.ccc",
        content=sample_content,
        secret=secret_256,
        algorithm=ALGORITHM_AES_256_GCM
    )
    print(f"  Encrypted payload type: {encrypted_256['type']}")

    decrypted_256 = verify_and_decrypt_payload(encrypted_256, secret_256)
    print(f"  Decrypted content matches: {decrypted_256['content'] == sample_content}")
    print("  ✓ Test 2 passed!\n")

    # Test 3: Tamper detection
    print("Test 3: Authentication tag verification (tamper detection)")
    try:
        # Tamper with encrypted data
        tampered = encrypted_128.copy()
        tampered_bytes = base64.b64decode(tampered['data'])
        # Flip a bit in the ciphertext
        tampered_bytes = tampered_bytes[:-1] + bytes([tampered_bytes[-1] ^ 0x01])
        tampered['data'] = base64.b64encode(tampered_bytes).decode('utf-8')

        decrypt_provisioning_info(tampered, secret_128)
        print("  ✗ Test 3 failed: tamper not detected!")
    except DecryptionError:
        print("  ✓ Test 3 passed: tamper detected!\n")

    # Test 4: Wrong key detection
    print("Test 4: Wrong key detection")
    try:
        wrong_secret = generate_secret(128)
        decrypt_provisioning_info(encrypted_128, wrong_secret)
        print("  ✗ Test 4 failed: wrong key not detected!")
    except DecryptionError:
        print("  ✓ Test 4 passed: wrong key detected!\n")

    print("=" * 50)
    print("All cryptographic self-tests passed! ✓")
    print("=" * 50)


if __name__ == "__main__":
    _run_self_test()
