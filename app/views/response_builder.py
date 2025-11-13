"""
Response Builder

Formats API responses.
Follows Single Responsibility: Response formatting only.
Follows Open/Closed: Easy to add new response types.
"""

from typing import Dict, Any, Tuple
from flask import jsonify, Response
from datetime import datetime, timezone

from app.models.mailbox import Mailbox
from app.config import HTTPStatus, AppConfig


class ResponseBuilder:
    """
    Builder for API responses.

    Follows Single Responsibility: Formats responses only.
    Follows Open/Closed: New response types can be added without modifying existing.
    """

    @staticmethod
    def success(data: Dict[str, Any], status_code: int = HTTPStatus.OK) -> Tuple[Response, int]:
        """
        Build success response.

        Args:
            data: Response data
            status_code: HTTP status code

        Returns:
            Flask response tuple
        """
        return jsonify(data), status_code

    @staticmethod
    def error(message: str, status_code: int = HTTPStatus.BAD_REQUEST) -> Tuple[Response, int]:
        """
        Build error response.

        Args:
            message: Error message
            status_code: HTTP status code

        Returns:
            Flask response tuple
        """
        return jsonify({"error": message}), status_code

    @staticmethod
    def created(data: Dict[str, Any]) -> Tuple[Response, int]:
        """
        Build created response (201).

        Args:
            data: Response data

        Returns:
            Flask response tuple
        """
        return ResponseBuilder.success(data, HTTPStatus.CREATED)

    @staticmethod
    def no_content() -> Tuple[str, int]:
        """
        Build no content response (200 with empty body).

        Returns:
            Flask response tuple
        """
        return '', HTTPStatus.OK

    @staticmethod
    def mailbox_created_response(mailbox: Mailbox, base_url: str) -> Tuple[Response, int]:
        """
        Build response for mailbox creation.

        Args:
            mailbox: Created mailbox
            base_url: Base URL for constructing mailbox URL

        Returns:
            Flask response tuple
        """
        url_link = f"{base_url}v1/m/{mailbox.mailbox_id}"

        return ResponseBuilder.success({
            "urlLink": url_link,
            "isPushNotificationSupported": True
        })

    @staticmethod
    def mailbox_updated_response() -> Tuple[Response, int]:
        """
        Build response for mailbox update.

        Returns:
            Flask response tuple
        """
        return ResponseBuilder.success({
            "isPushNotificationSupported": True
        })

    @staticmethod
    def mailbox_content_response(mailbox: Mailbox) -> Tuple[Response, int]:
        """
        Build response for reading mailbox content.

        Args:
            mailbox: Mailbox to read

        Returns:
            Flask response tuple
        """
        return ResponseBuilder.success({
            "displayInformation": mailbox.display_information,
            "payload": mailbox.payload,
            "expiration": mailbox.mailbox_configuration.expiration
        })

    @staticmethod
    def display_information_html(mailbox: Mailbox) -> Tuple[Response, int]:
        """
        Build HTML response for display information (OpenGraph format).

        Args:
            mailbox: Mailbox to display

        Returns:
            Flask response tuple with HTML
        """
        display_info = mailbox.display_information

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

        return Response(html, mimetype='text/html'), HTTPStatus.OK

    @staticmethod
    def health_response(mailbox_count: int) -> Tuple[Response, int]:
        """
        Build health check response.

        Args:
            mailbox_count: Number of active mailboxes

        Returns:
            Flask response tuple
        """
        return ResponseBuilder.success({
            "status": "healthy",
            "mailboxes": mailbox_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    @staticmethod
    def api_info_response() -> Tuple[Response, int]:
        """
        Build API information response.

        Returns:
            Flask response tuple
        """
        return ResponseBuilder.success({
            "service": AppConfig.SERVICE_NAME,
            "version": AppConfig.API_VERSION,
            "specification": AppConfig.SPECIFICATION,
            "endpoints": {
                "createMailbox": "POST /v1/m",
                "updateMailbox": "PUT /v1/m/{mailboxIdentifier}",
                "deleteMailbox": "DELETE /v1/m/{mailboxIdentifier}",
                "readDisplayInformation": "GET /v1/m/{mailboxIdentifier}",
                "readSecureContent": "POST /v1/m/{mailboxIdentifier}",
                "relinquishMailbox": "PATCH /v1/m/{mailboxIdentifier}",
                "health": "GET /health"
            },
            "documentation": f"https://datatracker.ietf.org/doc/html/{AppConfig.SPECIFICATION}"
        })
