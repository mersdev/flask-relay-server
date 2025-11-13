"""
Flask Relay Server for Secure Credential Transfer

This server implements the RFC draft-secure-credential-transfer-04 specification,
providing a secure relay mechanism for transferring encrypted credentials between devices.

Key Features:
- Stateless workflow (single transfer)
- Stateful workflow (multiple round-trips)
- Device claim-based authorization
- Request deduplication
- Automatic mailbox expiration
"""

from flask import Flask, request, jsonify, Response
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple, Any
import uuid
import logging
import json

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404

# Access Rights
ACCESS_READ = 'R'
ACCESS_WRITE = 'W'
ACCESS_DELETE = 'D'
DEFAULT_ACCESS_RIGHTS = 'RD'  # Read and Delete by default

# Required display information fields
REQUIRED_DISPLAY_FIELDS = ['title', 'description', 'imageURL']

# Required payload fields
REQUIRED_PAYLOAD_FIELDS = ['type', 'data']

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APPLICATION SETUP
# ============================================================================

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ============================================================================
# DATA STORAGE
# ============================================================================

# In-memory storage for mailboxes
# Structure: {mailbox_id: {payload, displayInformation, notificationToken, mailboxConfiguration, createdAt}}
mailboxes: Dict[str, Dict[str, Any]] = {}

# Device claims mapping
# Structure: {mailbox_id: {'sender': claim_uuid, 'receiver': claim_uuid}}
device_claims: Dict[str, Dict[str, Optional[str]]] = {}

# Request deduplication tracking
# Structure: {device_claim: last_processed_request_id}
processed_requests: Dict[str, str] = {}

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_uuid(uuid_string: Optional[str]) -> bool:
    """
    Validate if a string is a valid UUID v4.

    Args:
        uuid_string: String to validate

    Returns:
        True if valid UUID, False otherwise
    """
    if not uuid_string:
        return False

    try:
        uuid_obj = uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_display_information(display_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate display information structure.

    Args:
        display_info: Display information dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(display_info, dict):
        return False, "displayInformation must be a dictionary"

    missing_fields = [field for field in REQUIRED_DISPLAY_FIELDS if field not in display_info]
    if missing_fields:
        return False, f"displayInformation missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_payload(payload: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate payload structure.

    Args:
        payload: Payload dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(payload, dict):
        return False, "payload must be a dictionary"

    missing_fields = [field for field in REQUIRED_PAYLOAD_FIELDS if field not in payload]
    if missing_fields:
        return False, f"payload missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_expiration_format(expiration: str) -> Tuple[bool, Optional[str]]:
    """
    Validate expiration date format (ISO 8601).

    Args:
        expiration: Expiration timestamp string

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        datetime.fromisoformat(expiration.replace('Z', '+00:00'))
        return True, None
    except (ValueError, AttributeError, TypeError):
        return False, "Invalid expiration format. Use ISO 8601: YYYY-MM-DDThh:mm:ssZ"

# ============================================================================
# MAILBOX UTILITIES
# ============================================================================

def is_mailbox_expired(mailbox_data: Dict[str, Any]) -> bool:
    """
    Check if a mailbox has expired based on its expiration timestamp.

    Args:
        mailbox_data: Mailbox data dictionary

    Returns:
        True if expired, False otherwise
    """
    expiration_str = mailbox_data.get('mailboxConfiguration', {}).get('expiration')
    if not expiration_str:
        return False

    try:
        expiration_time = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expiration_time
    except (ValueError, AttributeError):
        logger.warning(f"Invalid expiration format in mailbox data: {expiration_str}")
        return False


def cleanup_expired_mailboxes() -> int:
    """
    Remove all expired mailboxes from storage.

    Returns:
        Number of mailboxes cleaned up
    """
    expired_mailbox_ids = [
        mailbox_id for mailbox_id, data in mailboxes.items()
        if is_mailbox_expired(data)
    ]

    for mailbox_id in expired_mailbox_ids:
        logger.info(f"Cleaning up expired mailbox: {mailbox_id}")
        mailboxes.pop(mailbox_id, None)
        device_claims.pop(mailbox_id, None)

    return len(expired_mailbox_ids)


def is_duplicate_request(device_claim: str, request_id: str) -> bool:
    """
    Check if a request is a duplicate based on device claim and request ID.

    Args:
        device_claim: Device claim UUID
        request_id: Request ID UUID

    Returns:
        True if duplicate, False otherwise
    """
    return (device_claim in processed_requests and
            processed_requests[device_claim] == request_id)


def has_access_right(mailbox_id: str, access_type: str) -> bool:
    """
    Check if a mailbox allows a specific type of access.

    Args:
        mailbox_id: Mailbox identifier
        access_type: Type of access (R, W, or D)

    Returns:
        True if access is allowed, False otherwise
    """
    if mailbox_id not in mailboxes:
        return False

    access_rights = mailboxes[mailbox_id]['mailboxConfiguration'].get(
        'accessRights',
        DEFAULT_ACCESS_RIGHTS
    )
    return access_type in access_rights


def is_device_authorized(mailbox_id: str, device_claim: str) -> bool:
    """
    Check if a device is authorized to access a mailbox.

    Args:
        mailbox_id: Mailbox identifier
        device_claim: Device claim UUID

    Returns:
        True if authorized, False otherwise
    """
    if mailbox_id not in device_claims:
        return False

    claims = device_claims[mailbox_id]
    return device_claim in [claims.get('sender'), claims.get('receiver')]


def find_mailbox_by_device_claim(device_claim: str) -> Optional[str]:
    """
    Find a mailbox ID associated with a sender device claim.

    Args:
        device_claim: Sender device claim UUID

    Returns:
        Mailbox ID if found, None otherwise
    """
    for mailbox_id, claims in device_claims.items():
        if claims.get('sender') == device_claim:
            return mailbox_id
    return None

# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.before_request
def before_request_handler():
    """
    Execute before each request to perform cleanup and logging.
    """
    # Clean up expired mailboxes
    cleaned = cleanup_expired_mailboxes()
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} expired mailbox(es)")


@app.after_request
def after_request_handler(response):
    """
    Execute after each request to add security headers.
    """
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/v1/m', methods=['POST'])
def create_mailbox():
    """
    Create a new mailbox for secure credential transfer.

    Endpoint: POST /v1/m

    Headers:
        Mailbox-Request-ID (required): UUID for request tracking
        Device-Claim (required): UUID for sender device
        Device-Attestation (optional): Device attestation data

    Request Body:
        {
            "payload": {"type": "...", "data": "..."},
            "displayInformation": {"title": "...", "description": "...", "imageURL": "..."},
            "mailboxConfiguration": {"accessRights": "RWD", "expiration": "..."},
            "notificationToken": {"type": "...", "tokenData": "..."} (optional)
        }

    Returns:
        200: Mailbox created successfully
        201: Duplicate request (mailbox already created)
        400: Invalid request
    """
    # ========================================
    # 1. Extract and validate headers
    # ========================================
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')
    device_attestation = request.headers.get('Device-Attestation')  # Optional

    if not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), HTTP_BAD_REQUEST

    if not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Check for duplicate requests
    # ========================================
    if is_duplicate_request(device_claim, mailbox_request_id):
        logger.info(f"Duplicate request detected: {mailbox_request_id}")
        mailbox_id = find_mailbox_by_device_claim(device_claim)

        if mailbox_id:
            url_link = f"{request.host_url}v1/m/{mailbox_id}"
            return jsonify({
                "urlLink": url_link,
                "isPushNotificationSupported": True
            }), HTTP_CREATED

    # ========================================
    # 3. Parse and validate request body
    # ========================================
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), HTTP_BAD_REQUEST
    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), HTTP_BAD_REQUEST

    # Validate payload
    if 'payload' not in data:
        return jsonify({"error": "payload is required"}), HTTP_BAD_REQUEST

    is_valid, error_msg = validate_payload(data['payload'])
    if not is_valid:
        return jsonify({"error": error_msg}), HTTP_BAD_REQUEST

    # Validate display information
    if 'displayInformation' not in data:
        return jsonify({"error": "displayInformation is required"}), HTTP_BAD_REQUEST

    is_valid, error_msg = validate_display_information(data['displayInformation'])
    if not is_valid:
        return jsonify({"error": error_msg}), HTTP_BAD_REQUEST

    # Validate mailbox configuration
    mailbox_config = data.get('mailboxConfiguration', {})
    if not mailbox_config.get('expiration'):
        return jsonify({"error": "mailboxConfiguration.expiration is required"}), HTTP_BAD_REQUEST

    is_valid, error_msg = validate_expiration_format(mailbox_config['expiration'])
    if not is_valid:
        return jsonify({"error": error_msg}), HTTP_BAD_REQUEST

    # ========================================
    # 4. Create mailbox
    # ========================================
    mailbox_id = str(uuid.uuid4())

    # Store mailbox data
    mailboxes[mailbox_id] = {
        'payload': data['payload'],
        'displayInformation': data['displayInformation'],
        'notificationToken': data.get('notificationToken'),
        'mailboxConfiguration': {
            'accessRights': mailbox_config.get('accessRights', DEFAULT_ACCESS_RIGHTS),
            'expiration': mailbox_config['expiration']
        },
        'createdAt': datetime.now(timezone.utc).isoformat()
    }

    # Bind sender device claim
    device_claims[mailbox_id] = {
        'sender': device_claim,
        'receiver': None
    }

    # Mark request as processed
    processed_requests[device_claim] = mailbox_request_id

    # ========================================
    # 5. Return response
    # ========================================
    url_link = f"{request.host_url}v1/m/{mailbox_id}"

    logger.info(f"Created mailbox {mailbox_id} for device {device_claim[:8]}...")

    return jsonify({
        "urlLink": url_link,
        "isPushNotificationSupported": True
    }), HTTP_OK


@app.route('/v1/m/<mailbox_id>', methods=['PUT'])
def update_mailbox(mailbox_id: str):
    """
    Update the secure content of an existing mailbox.

    Endpoint: PUT /v1/m/{mailboxIdentifier}

    This endpoint is used in stateful workflows where sender and receiver
    exchange multiple messages.

    Headers:
        Mailbox-Request-ID (required): UUID for request tracking
        Device-Claim (required): UUID for device (sender or receiver)

    Request Body:
        {
            "payload": {"type": "...", "data": "..."},
            "notificationToken": {"type": "...", "tokenData": "..."} (optional)
        }

    Returns:
        200: Mailbox updated successfully
        201: Duplicate request (already processed)
        400: Invalid request
        401: Unauthorized
        403: Write access forbidden
        404: Mailbox not found
    """
    # ========================================
    # 1. Validate mailbox ID
    # ========================================
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Extract and validate headers
    # ========================================
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')

    if not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), HTTP_BAD_REQUEST

    if not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), HTTP_BAD_REQUEST

    # ========================================
    # 3. Check mailbox existence
    # ========================================
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), HTTP_NOT_FOUND

    # ========================================
    # 4. Check authorization
    # ========================================
    if not is_device_authorized(mailbox_id, device_claim):
        logger.warning(f"Unauthorized update attempt on mailbox {mailbox_id}")
        return jsonify({"error": "Unauthorized"}), HTTP_UNAUTHORIZED

    # ========================================
    # 5. Check for duplicate requests
    # ========================================
    if is_duplicate_request(device_claim, mailbox_request_id):
        logger.info(f"Duplicate update request for mailbox {mailbox_id}")
        return jsonify({"isPushNotificationSupported": True}), HTTP_CREATED

    # ========================================
    # 6. Parse and validate request body
    # ========================================
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), HTTP_BAD_REQUEST
    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), HTTP_BAD_REQUEST

    if 'payload' not in data:
        return jsonify({"error": "payload is required"}), HTTP_BAD_REQUEST

    is_valid, error_msg = validate_payload(data['payload'])
    if not is_valid:
        return jsonify({"error": error_msg}), HTTP_BAD_REQUEST

    # ========================================
    # 7. Check write access
    # ========================================
    if not has_access_right(mailbox_id, ACCESS_WRITE):
        return jsonify({"error": "Write access not allowed for this mailbox"}), HTTP_FORBIDDEN

    # ========================================
    # 8. Update mailbox
    # ========================================
    mailboxes[mailbox_id]['payload'] = data['payload']

    # Update notification token if provided
    if 'notificationToken' in data:
        mailboxes[mailbox_id]['notificationToken'] = data['notificationToken']

    # Mark request as processed
    processed_requests[device_claim] = mailbox_request_id

    logger.info(f"Updated mailbox {mailbox_id} by device {device_claim[:8]}...")

    # Note: In production, send push notification here using the stored token
    # of the other device (sender or receiver)

    return jsonify({"isPushNotificationSupported": True}), HTTP_OK


@app.route('/v1/m/<mailbox_id>', methods=['DELETE'])
def delete_mailbox(mailbox_id: str):
    """
    Delete an existing mailbox.

    Endpoint: DELETE /v1/m/{mailboxIdentifier}

    This is typically called by the receiver after successfully provisioning
    the credential, or by the sender to cancel the transfer.

    Headers:
        Device-Claim (required): UUID for device (sender or receiver)

    Returns:
        200: Mailbox deleted successfully
        400: Invalid mailbox ID
        401: Unauthorized
        403: Delete access forbidden
        404: Mailbox not found
    """
    # ========================================
    # 1. Validate mailbox ID
    # ========================================
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Extract and validate headers
    # ========================================
    device_claim = request.headers.get('Device-Claim')

    if not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), HTTP_BAD_REQUEST

    # ========================================
    # 3. Check mailbox existence
    # ========================================
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), HTTP_NOT_FOUND

    # ========================================
    # 4. Check authorization
    # ========================================
    if not is_device_authorized(mailbox_id, device_claim):
        logger.warning(f"Unauthorized delete attempt on mailbox {mailbox_id}")
        return jsonify({"error": "Unauthorized"}), HTTP_UNAUTHORIZED

    # ========================================
    # 5. Check delete access
    # ========================================
    if not has_access_right(mailbox_id, ACCESS_DELETE):
        return jsonify({"error": "Delete access not allowed for this mailbox"}), HTTP_FORBIDDEN

    # ========================================
    # 6. Delete mailbox
    # ========================================
    mailboxes.pop(mailbox_id, None)
    device_claims.pop(mailbox_id, None)

    logger.info(f"Deleted mailbox {mailbox_id} by device {device_claim[:8]}...")

    return '', HTTP_OK


@app.route('/v1/m/<mailbox_id>', methods=['GET'])
def read_display_information(mailbox_id: str):
    """
    Read public display information from a mailbox.

    Endpoint: GET /v1/m/{mailboxIdentifier}

    Returns display information in OpenGraph format for rich previews
    in messaging applications.

    Returns:
        200: Display information (HTML)
        400: Invalid mailbox ID
        404: Mailbox not found
    """
    # ========================================
    # 1. Validate mailbox ID
    # ========================================
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Check mailbox existence
    # ========================================
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), HTTP_NOT_FOUND

    # ========================================
    # 3. Build OpenGraph HTML
    # ========================================
    display_info = mailboxes[mailbox_id].get('displayInformation', {})

    # Escape HTML to prevent XSS
    title = display_info.get('title', '').replace('"', '&quot;').replace('<', '&lt;')
    description = display_info.get('description', '').replace('"', '&quot;').replace('<', '&lt;')
    image_url = display_info.get('imageURL', '').replace('"', '&quot;')

    html = f"""<html prefix="og: https://ogp.me/ns#">
<head>
<title>{title}</title>
<meta property="og:title" content="{title}" />
<meta property="og:type" content="image/jpeg" />
<meta property="og:description" content="{description}" />
<meta property="og:url" content="share://" />
<meta property="og:image" content="{image_url}" />
<meta property="og:image:width" content="612" />
<meta property="og:image:height" content="408" />
</head>
</html>"""

    return Response(html, mimetype='text/html'), HTTP_OK


@app.route('/v1/m/<mailbox_id>', methods=['POST'])
def read_secure_content(mailbox_id: str):
    """
    Read encrypted secure content from a mailbox.

    Endpoint: POST /v1/m/{mailboxIdentifier}

    This endpoint binds the receiver device on first read and returns
    the encrypted provisioning information.

    Headers:
        Device-Claim (required): UUID for device (sender or receiver)

    Returns:
        200: Secure content retrieved successfully
        400: Invalid request
        401: Unauthorized
        403: Read access forbidden
        404: Mailbox not found
    """
    # ========================================
    # 1. Validate mailbox ID
    # ========================================
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Extract and validate headers
    # ========================================
    device_claim = request.headers.get('Device-Claim')

    if not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), HTTP_BAD_REQUEST

    # ========================================
    # 3. Check mailbox existence
    # ========================================
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), HTTP_NOT_FOUND

    # ========================================
    # 4. Handle receiver binding & authorization
    # ========================================
    claims = device_claims.get(mailbox_id, {})
    sender_claim = claims.get('sender')
    receiver_claim = claims.get('receiver')

    # If receiver not yet bound and this is not the sender, bind as receiver
    if receiver_claim is None and device_claim != sender_claim:
        device_claims[mailbox_id]['receiver'] = device_claim
        logger.info(f"Bound receiver {device_claim[:8]}... to mailbox {mailbox_id}")
    # Otherwise, check if device is authorized
    elif device_claim not in [sender_claim, receiver_claim]:
        logger.warning(f"Unauthorized read attempt on mailbox {mailbox_id}")
        return jsonify({"error": "Unauthorized"}), HTTP_UNAUTHORIZED

    # ========================================
    # 5. Check read access
    # ========================================
    if not has_access_right(mailbox_id, ACCESS_READ):
        return jsonify({"error": "Read access not allowed for this mailbox"}), HTTP_FORBIDDEN

    # ========================================
    # 6. Prepare and return response
    # ========================================
    mailbox_data = mailboxes[mailbox_id]

    response_data = {
        "displayInformation": mailbox_data['displayInformation'],
        "payload": mailbox_data['payload'],
        "expiration": mailbox_data['mailboxConfiguration']['expiration']
    }

    logger.info(f"Device {device_claim[:8]}... read from mailbox {mailbox_id}")

    return jsonify(response_data), HTTP_OK


@app.route('/v1/m/<mailbox_id>', methods=['PATCH'])
def relinquish_mailbox(mailbox_id: str):
    """
    Relinquish receiver ownership of a mailbox.

    Endpoint: PATCH /v1/m/{mailboxIdentifier}

    This allows a receiver to unbind from a mailbox, enabling another
    receiver to bind to it.

    Headers:
        Mailbox-Request-ID (required): UUID for request tracking
        Device-Claim (required): UUID for receiver device

    Returns:
        200: Mailbox relinquished successfully
        201: Duplicate request (already processed)
        400: Invalid request
        401: Unauthorized (not receiver or not bound)
        404: Mailbox not found
    """
    # ========================================
    # 1. Validate mailbox ID
    # ========================================
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), HTTP_BAD_REQUEST

    # ========================================
    # 2. Extract and validate headers
    # ========================================
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')

    if not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), HTTP_BAD_REQUEST

    if not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), HTTP_BAD_REQUEST

    # ========================================
    # 3. Check mailbox existence
    # ========================================
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), HTTP_NOT_FOUND

    # ========================================
    # 4. Check if device is the receiver
    # ========================================
    claims = device_claims.get(mailbox_id, {})
    if claims.get('receiver') != device_claim:
        logger.warning(f"Non-receiver attempted to relinquish mailbox {mailbox_id}")
        return jsonify({"error": "Unauthorized - only receiver can relinquish mailbox"}), HTTP_UNAUTHORIZED

    # ========================================
    # 5. Check for duplicate requests
    # ========================================
    if is_duplicate_request(device_claim, mailbox_request_id):
        logger.info(f"Duplicate relinquish request for mailbox {mailbox_id}")
        return '', HTTP_CREATED

    # ========================================
    # 6. Relinquish receiver claim
    # ========================================
    device_claims[mailbox_id]['receiver'] = None
    processed_requests[device_claim] = mailbox_request_id

    logger.info(f"Device {device_claim[:8]}... relinquished mailbox {mailbox_id}")

    return '', HTTP_OK

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        200: Server status and statistics
    """
    return jsonify({
        "status": "healthy",
        "mailboxes": len(mailboxes),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), HTTP_OK


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint with API documentation.

    Returns:
        200: API information and available endpoints
    """
    return jsonify({
        "service": "Secure Credential Transfer Relay Server",
        "version": "v1",
        "specification": "draft-secure-credential-transfer-04",
        "endpoints": {
            "createMailbox": "POST /v1/m",
            "updateMailbox": "PUT /v1/m/{mailboxIdentifier}",
            "deleteMailbox": "DELETE /v1/m/{mailboxIdentifier}",
            "readDisplayInformation": "GET /v1/m/{mailboxIdentifier}",
            "readSecureContent": "POST /v1/m/{mailboxIdentifier}",
            "relinquishMailbox": "PATCH /v1/m/{mailboxIdentifier}",
            "health": "GET /health"
        },
        "documentation": "https://datatracker.ietf.org/doc/html/draft-secure-credential-transfer-04"
    }), HTTP_OK

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Secure Credential Transfer Relay Server")
    logger.info("Server will be available at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
