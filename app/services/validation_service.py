"""
Validation Service

Input validation logic.
Follows Single Responsibility: Validation only.
Follows Open/Closed: Easy to extend with new validators.
"""

from typing import Tuple, Optional, Dict, Any
from datetime import datetime
import uuid

from app.config import ValidationRules


class ValidationService:
    """
    Service for input validation.

    Follows Single Responsibility: Validation logic only.
    Follows Open/Closed: New validators can be added without modifying existing code.
    """

    @staticmethod
    def validate_uuid(uuid_string: Optional[str]) -> bool:
        """
        Validate if string is a valid UUID v4.

        Args:
            uuid_string: String to validate

        Returns:
            True if valid UUID, False otherwise
        """
        if not uuid_string:
            return False

        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    @staticmethod
    def validate_display_information(
        display_info: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate display information structure.

        Args:
            display_info: Display information to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(display_info, dict):
            return False, "displayInformation must be a dictionary"

        missing_fields = [
            field for field in ValidationRules.REQUIRED_DISPLAY_FIELDS
            if field not in display_info
        ]

        if missing_fields:
            return False, f"displayInformation missing required fields: {', '.join(missing_fields)}"

        return True, None

    @staticmethod
    def validate_payload(payload: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate payload structure.

        Args:
            payload: Payload to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(payload, dict):
            return False, "payload must be a dictionary"

        missing_fields = [
            field for field in ValidationRules.REQUIRED_PAYLOAD_FIELDS
            if field not in payload
        ]

        if missing_fields:
            return False, f"payload missing required fields: {', '.join(missing_fields)}"

        return True, None

    @staticmethod
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

    @staticmethod
    def validate_mailbox_configuration(
        config: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate mailbox configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not config.get('expiration'):
            return False, "mailboxConfiguration.expiration is required"

        return ValidationService.validate_expiration_format(config['expiration'])

    @staticmethod
    def validate_create_mailbox_request(
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate complete create mailbox request.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate payload
        if 'payload' not in data:
            return False, "payload is required"

        is_valid, error_msg = ValidationService.validate_payload(data['payload'])
        if not is_valid:
            return False, error_msg

        # Validate display information
        if 'displayInformation' not in data:
            return False, "displayInformation is required"

        is_valid, error_msg = ValidationService.validate_display_information(
            data['displayInformation']
        )
        if not is_valid:
            return False, error_msg

        # Validate mailbox configuration
        mailbox_config = data.get('mailboxConfiguration', {})
        is_valid, error_msg = ValidationService.validate_mailbox_configuration(mailbox_config)
        if not is_valid:
            return False, error_msg

        return True, None

    @staticmethod
    def validate_update_mailbox_request(
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate update mailbox request.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if 'payload' not in data:
            return False, "payload is required"

        return ValidationService.validate_payload(data['payload'])
