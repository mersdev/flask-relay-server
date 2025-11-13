"""
Mailbox Controller

Handles mailbox HTTP requests.
Follows Single Responsibility: Request/response coordination only.
Follows Dependency Inversion: Depends on service abstractions.
"""

from flask import request, Blueprint
from typing import Tuple, Any
import logging

from app.services.mailbox_service import MailboxService
from app.services.validation_service import ValidationService
from app.services.deduplication_service import DeduplicationService
from app.views.response_builder import ResponseBuilder
from app.config import HTTPStatus, AccessRights

logger = logging.getLogger(__name__)


class MailboxController:
    """
    Controller for mailbox endpoints.

    Follows Single Responsibility: Handles HTTP requests for mailboxes.
    Follows Dependency Inversion: Depends on service interfaces.
    """

    def __init__(
        self,
        mailbox_service: MailboxService,
        validation_service: ValidationService,
        deduplication_service: DeduplicationService
    ):
        """
        Initialize controller with dependencies.

        Args:
            mailbox_service: Service for mailbox operations
            validation_service: Service for validation
            deduplication_service: Service for deduplication
        """
        self._mailbox_service = mailbox_service
        self._validation_service = validation_service
        self._deduplication_service = deduplication_service
        self._response_builder = ResponseBuilder()

    def create_mailbox(self) -> Tuple[Any, int]:
        """
        Handle POST /v1/m - Create mailbox.

        Returns:
            Flask response tuple
        """
        # Extract and validate headers
        mailbox_request_id = request.headers.get('Mailbox-Request-ID')
        device_claim = request.headers.get('Device-Claim')

        if not self._validation_service.validate_uuid(mailbox_request_id):
            return self._response_builder.error(
                "Invalid or missing Mailbox-Request-ID header",
                HTTPStatus.BAD_REQUEST
            )

        if not self._validation_service.validate_uuid(device_claim):
            return self._response_builder.error(
                "Invalid or missing Device-Claim header",
                HTTPStatus.BAD_REQUEST
            )

        # Check for duplicate requests
        if self._deduplication_service.is_duplicate_request(device_claim, mailbox_request_id):
            logger.info(f"Duplicate request detected: {mailbox_request_id}")
            mailbox = self._mailbox_service.find_mailbox_by_sender_claim(device_claim)

            if mailbox:
                url_link = f"{request.host_url}v1/m/{mailbox.mailbox_id}"
                return self._response_builder.success({
                    "urlLink": url_link,
                    "isPushNotificationSupported": True
                }, HTTPStatus.CREATED)

        # Parse and validate request body
        try:
            data = request.get_json()
            if not data:
                return self._response_builder.error("Request body is required")
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return self._response_builder.error(f"Invalid JSON: {str(e)}")

        # Validate request
        is_valid, error_msg = self._validation_service.validate_create_mailbox_request(data)
        if not is_valid:
            return self._response_builder.error(error_msg)

        # Create mailbox
        try:
            mailbox = self._mailbox_service.create_mailbox(
                payload=data['payload'],
                display_information=data['displayInformation'],
                mailbox_configuration=data.get('mailboxConfiguration', {}),
                sender_device_claim=device_claim,
                notification_token=data.get('notificationToken')
            )

            # Mark request as processed
            self._deduplication_service.mark_request_processed(device_claim, mailbox_request_id)

            return self._response_builder.mailbox_created_response(mailbox, request.host_url)

        except Exception as e:
            logger.error(f"Error creating mailbox: {str(e)}")
            return self._response_builder.error(f"Failed to create mailbox: {str(e)}")

    def update_mailbox(self, mailbox_id: str) -> Tuple[Any, int]:
        """
        Handle PUT /v1/m/{mailboxIdentifier} - Update mailbox.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Flask response tuple
        """
        # Validate mailbox ID
        if not self._validation_service.validate_uuid(mailbox_id):
            return self._response_builder.error(
                "Invalid mailbox identifier",
                HTTPStatus.BAD_REQUEST
            )

        # Extract and validate headers
        mailbox_request_id = request.headers.get('Mailbox-Request-ID')
        device_claim = request.headers.get('Device-Claim')

        if not self._validation_service.validate_uuid(mailbox_request_id):
            return self._response_builder.error(
                "Invalid or missing Mailbox-Request-ID header",
                HTTPStatus.BAD_REQUEST
            )

        if not self._validation_service.validate_uuid(device_claim):
            return self._response_builder.error(
                "Invalid or missing Device-Claim header",
                HTTPStatus.BAD_REQUEST
            )

        # Check if mailbox exists
        mailbox = self._mailbox_service.find_mailbox(mailbox_id)
        if not mailbox:
            return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        # Check authorization
        if not self._mailbox_service.is_device_authorized(mailbox_id, device_claim):
            logger.warning(f"Unauthorized update attempt on mailbox {mailbox_id}")
            return self._response_builder.error("Unauthorized", HTTPStatus.UNAUTHORIZED)

        # Check for duplicate requests
        if self._deduplication_service.is_duplicate_request(device_claim, mailbox_request_id):
            logger.info(f"Duplicate update request for mailbox {mailbox_id}")
            return self._response_builder.mailbox_updated_response(), HTTPStatus.CREATED

        # Parse and validate request body
        try:
            data = request.get_json()
            if not data:
                return self._response_builder.error("Request body is required")
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return self._response_builder.error(f"Invalid JSON: {str(e)}")

        # Validate request
        is_valid, error_msg = self._validation_service.validate_update_mailbox_request(data)
        if not is_valid:
            return self._response_builder.error(error_msg)

        # Check write access
        if not self._mailbox_service.has_access_right(mailbox_id, AccessRights.WRITE):
            return self._response_builder.error(
                "Write access not allowed for this mailbox",
                HTTPStatus.FORBIDDEN
            )

        # Update mailbox
        try:
            self._mailbox_service.update_mailbox_payload(
                mailbox_id=mailbox_id,
                new_payload=data['payload'],
                notification_token=data.get('notificationToken')
            )

            # Mark request as processed
            self._deduplication_service.mark_request_processed(device_claim, mailbox_request_id)

            logger.info(f"Updated mailbox {mailbox_id} by device {device_claim[:8]}...")

            return self._response_builder.mailbox_updated_response()

        except Exception as e:
            logger.error(f"Error updating mailbox: {str(e)}")
            return self._response_builder.error(f"Failed to update mailbox: {str(e)}")

    def delete_mailbox(self, mailbox_id: str) -> Tuple[Any, int]:
        """
        Handle DELETE /v1/m/{mailboxIdentifier} - Delete mailbox.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Flask response tuple
        """
        # Validate mailbox ID
        if not self._validation_service.validate_uuid(mailbox_id):
            return self._response_builder.error(
                "Invalid mailbox identifier",
                HTTPStatus.BAD_REQUEST
            )

        # Extract and validate headers
        device_claim = request.headers.get('Device-Claim')

        if not self._validation_service.validate_uuid(device_claim):
            return self._response_builder.error(
                "Invalid or missing Device-Claim header",
                HTTPStatus.BAD_REQUEST
            )

        # Check if mailbox exists
        if not self._mailbox_service.find_mailbox(mailbox_id):
            return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        # Check authorization
        if not self._mailbox_service.is_device_authorized(mailbox_id, device_claim):
            logger.warning(f"Unauthorized delete attempt on mailbox {mailbox_id}")
            return self._response_builder.error("Unauthorized", HTTPStatus.UNAUTHORIZED)

        # Check delete access
        if not self._mailbox_service.has_access_right(mailbox_id, AccessRights.DELETE):
            return self._response_builder.error(
                "Delete access not allowed for this mailbox",
                HTTPStatus.FORBIDDEN
            )

        # Delete mailbox
        try:
            deleted = self._mailbox_service.delete_mailbox(mailbox_id)

            if deleted:
                logger.info(f"Deleted mailbox {mailbox_id} by device {device_claim[:8]}...")
                return self._response_builder.no_content()
            else:
                return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        except Exception as e:
            logger.error(f"Error deleting mailbox: {str(e)}")
            return self._response_builder.error(f"Failed to delete mailbox: {str(e)}")

    def read_display_information(self, mailbox_id: str) -> Tuple[Any, int]:
        """
        Handle GET /v1/m/{mailboxIdentifier} - Read display information.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Flask response tuple with HTML
        """
        # Validate mailbox ID
        if not self._validation_service.validate_uuid(mailbox_id):
            return self._response_builder.error(
                "Invalid mailbox identifier",
                HTTPStatus.BAD_REQUEST
            )

        # Find mailbox
        mailbox = self._mailbox_service.find_mailbox(mailbox_id)
        if not mailbox:
            return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        # Return HTML response
        return self._response_builder.display_information_html(mailbox)

    def read_secure_content(self, mailbox_id: str) -> Tuple[Any, int]:
        """
        Handle POST /v1/m/{mailboxIdentifier} - Read secure content.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Flask response tuple
        """
        # Validate mailbox ID
        if not self._validation_service.validate_uuid(mailbox_id):
            return self._response_builder.error(
                "Invalid mailbox identifier",
                HTTPStatus.BAD_REQUEST
            )

        # Extract and validate headers
        device_claim = request.headers.get('Device-Claim')

        if not self._validation_service.validate_uuid(device_claim):
            return self._response_builder.error(
                "Invalid or missing Device-Claim header",
                HTTPStatus.BAD_REQUEST
            )

        # Find mailbox
        mailbox = self._mailbox_service.find_mailbox(mailbox_id)
        if not mailbox:
            return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        # Bind receiver if needed
        self._mailbox_service.bind_receiver_if_needed(mailbox_id, device_claim)

        # Check authorization
        if not self._mailbox_service.is_device_authorized(mailbox_id, device_claim):
            logger.warning(f"Unauthorized read attempt on mailbox {mailbox_id}")
            return self._response_builder.error("Unauthorized", HTTPStatus.UNAUTHORIZED)

        # Check read access
        if not self._mailbox_service.has_access_right(mailbox_id, AccessRights.READ):
            return self._response_builder.error(
                "Read access not allowed for this mailbox",
                HTTPStatus.FORBIDDEN
            )

        # Return secure content
        logger.info(f"Device {device_claim[:8]}... read from mailbox {mailbox_id}")
        return self._response_builder.mailbox_content_response(mailbox)

    def relinquish_mailbox(self, mailbox_id: str) -> Tuple[Any, int]:
        """
        Handle PATCH /v1/m/{mailboxIdentifier} - Relinquish mailbox.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Flask response tuple
        """
        # Validate mailbox ID
        if not self._validation_service.validate_uuid(mailbox_id):
            return self._response_builder.error(
                "Invalid mailbox identifier",
                HTTPStatus.BAD_REQUEST
            )

        # Extract and validate headers
        mailbox_request_id = request.headers.get('Mailbox-Request-ID')
        device_claim = request.headers.get('Device-Claim')

        if not self._validation_service.validate_uuid(mailbox_request_id):
            return self._response_builder.error(
                "Invalid or missing Mailbox-Request-ID header",
                HTTPStatus.BAD_REQUEST
            )

        if not self._validation_service.validate_uuid(device_claim):
            return self._response_builder.error(
                "Invalid or missing Device-Claim header",
                HTTPStatus.BAD_REQUEST
            )

        # Check if mailbox exists
        if not self._mailbox_service.find_mailbox(mailbox_id):
            return self._response_builder.error("Mailbox not found", HTTPStatus.NOT_FOUND)

        # Check for duplicate requests
        if self._deduplication_service.is_duplicate_request(device_claim, mailbox_request_id):
            logger.info(f"Duplicate relinquish request for mailbox {mailbox_id}")
            return '', HTTPStatus.CREATED

        # Relinquish receiver
        try:
            self._mailbox_service.relinquish_receiver(mailbox_id, device_claim)

            # Mark request as processed
            self._deduplication_service.mark_request_processed(device_claim, mailbox_request_id)

            return self._response_builder.no_content()

        except ValueError as e:
            logger.warning(f"Relinquish error: {str(e)}")
            return self._response_builder.error(str(e), HTTPStatus.UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Error relinquishing mailbox: {str(e)}")
            return self._response_builder.error(f"Failed to relinquish mailbox: {str(e)}")


def create_mailbox_blueprint(controller: MailboxController) -> Blueprint:
    """
    Create Flask blueprint for mailbox routes.

    Args:
        controller: Mailbox controller instance

    Returns:
        Flask blueprint
    """
    bp = Blueprint('mailbox', __name__)

    @bp.route('/v1/m', methods=['POST'])
    def create():
        return controller.create_mailbox()

    @bp.route('/v1/m/<mailbox_id>', methods=['PUT'])
    def update(mailbox_id: str):
        return controller.update_mailbox(mailbox_id)

    @bp.route('/v1/m/<mailbox_id>', methods=['DELETE'])
    def delete(mailbox_id: str):
        return controller.delete_mailbox(mailbox_id)

    @bp.route('/v1/m/<mailbox_id>', methods=['GET'])
    def display(mailbox_id: str):
        return controller.read_display_information(mailbox_id)

    @bp.route('/v1/m/<mailbox_id>', methods=['POST'])
    def read(mailbox_id: str):
        return controller.read_secure_content(mailbox_id)

    @bp.route('/v1/m/<mailbox_id>', methods=['PATCH'])
    def relinquish(mailbox_id: str):
        return controller.relinquish_mailbox(mailbox_id)

    return bp
