"""
Flask Relay Server for Secure Credential Transfer
Implements the Internet-Draft: draft-secure-credential-transfer-04
"""

from flask import Flask, request, jsonify, Response
from datetime import datetime, timezone
import uuid
import logging
from typing import Dict, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# In-memory storage for mailboxes
# Structure: {mailbox_id: {mailbox_data}}
mailboxes: Dict[str, dict] = {}

# Store device claims for each mailbox
# Structure: {mailbox_id: {'sender': claim, 'receiver': claim}}
device_claims: Dict[str, dict] = {}

# Store last processed request IDs per device claim
# Structure: {device_claim: mailbox_request_id}
processed_requests: Dict[str, str] = {}


def validate_uuid(uuid_string: str) -> bool:
    """Validate if string is a valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def check_mailbox_expired(mailbox_data: dict) -> bool:
    """Check if mailbox has expired"""
    expiration_str = mailbox_data.get('mailboxConfiguration', {}).get('expiration')
    if not expiration_str:
        return False

    try:
        expiration_time = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expiration_time
    except (ValueError, AttributeError):
        return False


def cleanup_expired_mailboxes():
    """Remove expired mailboxes"""
    expired = [mid for mid, data in mailboxes.items() if check_mailbox_expired(data)]
    for mid in expired:
        logger.info(f"Deleting expired mailbox: {mid}")
        mailboxes.pop(mid, None)
        device_claims.pop(mid, None)


@app.before_request
def before_request():
    """Cleanup expired mailboxes before each request"""
    cleanup_expired_mailboxes()


@app.route('/v1/m', methods=['POST'])
def create_mailbox():
    """
    CreateMailbox endpoint
    POST /v1/m

    Creates a new mailbox and stores encrypted provisioning information
    """
    # Get headers
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')
    device_attestation = request.headers.get('Device-Attestation')

    # Validate required headers
    if not mailbox_request_id or not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), 400

    if not device_claim or not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), 400

    # Check for duplicate request
    if device_claim in processed_requests and processed_requests[device_claim] == mailbox_request_id:
        logger.info(f"Duplicate request detected for Device-Claim: {device_claim}")
        # Find the mailbox associated with this device claim
        for mailbox_id, claims in device_claims.items():
            if claims.get('sender') == device_claim:
                url_link = f"{request.host_url}v1/m/{mailbox_id}"
                return jsonify({
                    "urlLink": url_link,
                    "isPushNotificationSupported": True
                }), 201

    # Parse request body
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    # Validate required fields
    if 'payload' not in data:
        return jsonify({"error": "payload is required"}), 400

    if 'displayInformation' not in data:
        return jsonify({"error": "displayInformation is required"}), 400

    display_info = data['displayInformation']
    if not all(k in display_info for k in ['title', 'description', 'imageURL']):
        return jsonify({"error": "displayInformation must contain title, description, and imageURL"}), 400

    # Validate payload structure
    payload = data['payload']
    if not isinstance(payload, dict) or 'type' not in payload or 'data' not in payload:
        return jsonify({"error": "payload must contain type and data fields"}), 400

    # Validate mailboxConfiguration
    mailbox_config = data.get('mailboxConfiguration', {})
    if not mailbox_config.get('expiration'):
        return jsonify({"error": "mailboxConfiguration.expiration is required"}), 400

    # Validate expiration format
    try:
        datetime.fromisoformat(mailbox_config['expiration'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid expiration format. Use YYYY-MM-DDThh:mm:ssZ"}), 400

    # Generate unique mailbox identifier
    mailbox_id = str(uuid.uuid4())

    # Store mailbox data
    mailboxes[mailbox_id] = {
        'payload': payload,
        'displayInformation': display_info,
        'notificationToken': data.get('notificationToken'),
        'mailboxConfiguration': {
            'accessRights': mailbox_config.get('accessRights', 'RD'),
            'expiration': mailbox_config['expiration']
        },
        'createdAt': datetime.now(timezone.utc).isoformat()
    }

    # Store sender device claim
    device_claims[mailbox_id] = {
        'sender': device_claim,
        'receiver': None
    }

    # Store processed request ID
    processed_requests[device_claim] = mailbox_request_id

    # Build URL link to mailbox
    url_link = f"{request.host_url}v1/m/{mailbox_id}"

    logger.info(f"Created mailbox: {mailbox_id}")

    return jsonify({
        "urlLink": url_link,
        "isPushNotificationSupported": True
    }), 200


@app.route('/v1/m/<mailbox_id>', methods=['PUT'])
def update_mailbox(mailbox_id: str):
    """
    UpdateMailbox endpoint
    PUT /v1/m/{mailboxIdentifier}

    Updates secure content in an existing mailbox
    """
    # Validate mailbox_id
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), 400

    # Get headers
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')

    # Validate required headers
    if not mailbox_request_id or not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), 400

    if not device_claim or not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), 400

    # Check if mailbox exists
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), 404

    # Check authorization
    claims = device_claims.get(mailbox_id, {})
    if device_claim not in [claims.get('sender'), claims.get('receiver')]:
        return jsonify({"error": "Unauthorized"}), 401

    # Check for duplicate request
    if device_claim in processed_requests and processed_requests[device_claim] == mailbox_request_id:
        logger.info(f"Duplicate update request for mailbox: {mailbox_id}")
        return jsonify({
            "isPushNotificationSupported": True
        }), 201

    # Parse request body
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    # Validate required fields
    if 'payload' not in data:
        return jsonify({"error": "payload is required"}), 400

    payload = data['payload']
    if not isinstance(payload, dict) or 'type' not in payload or 'data' not in payload:
        return jsonify({"error": "payload must contain type and data fields"}), 400

    # Check write access
    access_rights = mailboxes[mailbox_id]['mailboxConfiguration'].get('accessRights', 'RD')
    if 'W' not in access_rights:
        return jsonify({"error": "Write access not allowed for this mailbox"}), 403

    # Update mailbox
    mailboxes[mailbox_id]['payload'] = payload
    if 'notificationToken' in data:
        mailboxes[mailbox_id]['notificationToken'] = data['notificationToken']

    # Store processed request ID
    processed_requests[device_claim] = mailbox_request_id

    logger.info(f"Updated mailbox: {mailbox_id}")

    # In a real implementation, we would send push notification here
    # using the notification token stored by the other device

    return jsonify({
        "isPushNotificationSupported": True
    }), 200


@app.route('/v1/m/<mailbox_id>', methods=['DELETE'])
def delete_mailbox(mailbox_id: str):
    """
    DeleteMailbox endpoint
    DELETE /v1/m/{mailboxIdentifier}

    Deletes an existing mailbox
    """
    # Validate mailbox_id
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), 400

    # Get headers
    device_claim = request.headers.get('Device-Claim')

    # Validate required headers
    if not device_claim or not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), 400

    # Check if mailbox exists
    if mailbox_id not in mailboxes:
        # Return 404 for non-existent mailbox
        return jsonify({"error": "Mailbox not found"}), 404

    # Check authorization
    claims = device_claims.get(mailbox_id, {})
    if device_claim not in [claims.get('sender'), claims.get('receiver')]:
        return jsonify({"error": "Unauthorized"}), 401

    # Check delete access
    access_rights = mailboxes[mailbox_id]['mailboxConfiguration'].get('accessRights', 'RD')
    if 'D' not in access_rights:
        return jsonify({"error": "Delete access not allowed for this mailbox"}), 403

    # Delete mailbox
    mailboxes.pop(mailbox_id, None)
    device_claims.pop(mailbox_id, None)

    logger.info(f"Deleted mailbox: {mailbox_id}")

    return '', 200


@app.route('/v1/m/<mailbox_id>', methods=['GET'])
def read_display_information(mailbox_id: str):
    """
    ReadDisplayInformationFromMailbox endpoint
    GET /v1/m/{mailboxIdentifier}

    Returns public display information in OpenGraph format
    """
    # Validate mailbox_id
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), 400

    # Check if mailbox exists
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), 404

    # Get display information
    display_info = mailboxes[mailbox_id].get('displayInformation', {})

    # Build OpenGraph HTML
    html = f"""<html prefix="og: https://ogp.me/ns#">
<head>
<title>{display_info.get('title', '')}</title>
<meta property="og:title" content="{display_info.get('title', '')}" />
<meta property="og:type" content="image/jpeg" />
<meta property="og:description" content="{display_info.get('description', '')}" />
<meta property="og:url" content="share://" />
<meta property="og:image" content="{display_info.get('imageURL', '')}" />
<meta property="og:image:width" content="612" />
<meta property="og:image:height" content="408" />
</head>
</html>"""

    return Response(html, mimetype='text/html'), 200


@app.route('/v1/m/<mailbox_id>', methods=['POST'])
def read_secure_content(mailbox_id: str):
    """
    ReadSecureContentFromMailbox endpoint
    POST /v1/m/{mailboxIdentifier}

    Returns encrypted provisioning information from mailbox
    """
    # Validate mailbox_id
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), 400

    # Get headers
    device_claim = request.headers.get('Device-Claim')

    # Validate required headers
    if not device_claim or not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), 400

    # Check if mailbox exists
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), 404

    # Check authorization and bind receiver if first time
    claims = device_claims.get(mailbox_id, {})

    # If receiver not yet bound, bind this device as receiver
    if claims.get('receiver') is None and device_claim != claims.get('sender'):
        device_claims[mailbox_id]['receiver'] = device_claim
        logger.info(f"Bound receiver to mailbox: {mailbox_id}")
    elif device_claim not in [claims.get('sender'), claims.get('receiver')]:
        return jsonify({"error": "Unauthorized"}), 401

    # Check read access
    access_rights = mailboxes[mailbox_id]['mailboxConfiguration'].get('accessRights', 'RD')
    if 'R' not in access_rights:
        return jsonify({"error": "Read access not allowed for this mailbox"}), 403

    # Get mailbox data
    mailbox_data = mailboxes[mailbox_id]

    response_data = {
        "displayInformation": mailbox_data['displayInformation'],
        "payload": mailbox_data['payload'],
        "expiration": mailbox_data['mailboxConfiguration']['expiration']
    }

    logger.info(f"Read secure content from mailbox: {mailbox_id}")

    return jsonify(response_data), 200


@app.route('/v1/m/<mailbox_id>', methods=['PATCH'])
def relinquish_mailbox(mailbox_id: str):
    """
    RelinquishMailbox endpoint
    PATCH /v1/m/{mailboxIdentifier}

    Allows receiver to relinquish ownership of the mailbox
    """
    # Validate mailbox_id
    if not validate_uuid(mailbox_id):
        return jsonify({"error": "Invalid mailbox identifier"}), 400

    # Get headers
    mailbox_request_id = request.headers.get('Mailbox-Request-ID')
    device_claim = request.headers.get('Device-Claim')

    # Validate required headers
    if not mailbox_request_id or not validate_uuid(mailbox_request_id):
        return jsonify({"error": "Invalid or missing Mailbox-Request-ID header"}), 400

    if not device_claim or not validate_uuid(device_claim):
        return jsonify({"error": "Invalid or missing Device-Claim header"}), 400

    # Check if mailbox exists
    if mailbox_id not in mailboxes:
        return jsonify({"error": "Mailbox not found"}), 404

    # Check if device is the receiver
    claims = device_claims.get(mailbox_id, {})
    if claims.get('receiver') != device_claim:
        return jsonify({"error": "Unauthorized - only receiver can relinquish mailbox"}), 401

    # Check for duplicate request
    if device_claim in processed_requests and processed_requests[device_claim] == mailbox_request_id:
        logger.info(f"Duplicate relinquish request for mailbox: {mailbox_id}")
        return '', 201

    # Relinquish receiver claim
    device_claims[mailbox_id]['receiver'] = None

    # Store processed request ID
    processed_requests[device_claim] = mailbox_request_id

    logger.info(f"Relinquished mailbox: {mailbox_id}")

    return '', 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "mailboxes": len(mailboxes),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information"""
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
            "relinquishMailbox": "PATCH /v1/m/{mailboxIdentifier}"
        }
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
