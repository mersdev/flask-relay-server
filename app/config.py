"""
Configuration Module

Contains all application constants and configuration settings.
Following SOLID principles: Single Responsibility - Configuration only.
"""

from typing import Dict, List

# ============================================================================
# HTTP STATUS CODES
# ============================================================================

class HTTPStatus:
    """HTTP status code constants."""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404


# ============================================================================
# ACCESS RIGHTS
# ============================================================================

class AccessRights:
    """Mailbox access rights constants."""
    READ = 'R'
    WRITE = 'W'
    DELETE = 'D'
    DEFAULT = 'RD'  # Read and Delete by default


# ============================================================================
# ENCRYPTION ALGORITHMS
# ============================================================================

class EncryptionAlgorithms:
    """Supported encryption algorithms."""
    AES_128_GCM = "AEAD_AES_128_GCM"
    AES_256_GCM = "AEAD_AES_256_GCM"


# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

class ValidationRules:
    """Validation rules and required fields."""
    REQUIRED_DISPLAY_FIELDS: List[str] = ['title', 'description', 'imageURL']
    REQUIRED_PAYLOAD_FIELDS: List[str] = ['type', 'data']
    REQUIRED_PROV_INFO_FIELDS: List[str] = ['format', 'content']


# ============================================================================
# CRYPTOGRAPHY CONSTANTS
# ============================================================================

class CryptoConfig:
    """Cryptography configuration constants."""
    KEY_SIZE_128_BITS = 16  # 128 bits = 16 bytes
    KEY_SIZE_256_BITS = 32  # 256 bits = 32 bytes
    IV_SIZE = 12  # 96 bits = 12 bytes (recommended for AES-GCM)
    TAG_SIZE = 16  # 128 bits = 16 bytes


# ============================================================================
# APPLICATION CONFIG
# ============================================================================

class AppConfig:
    """Application configuration."""
    API_VERSION = "v1"
    SERVICE_NAME = "Secure Credential Transfer Relay Server"
    SPECIFICATION = "draft-secure-credential-transfer-04"
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 5000
    DEBUG = True


# ============================================================================
# SECURITY HEADERS
# ============================================================================

class SecurityHeaders:
    """Security headers to add to responses."""
    HEADERS: Dict[str, str] = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }
