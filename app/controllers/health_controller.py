"""
Health Controller

Handles health check and utility endpoints.
Follows Single Responsibility: Utility endpoints only.
"""

from flask import Blueprint
from typing import Tuple, Any

from app.services.mailbox_service import MailboxService
from app.views.response_builder import ResponseBuilder


class HealthController:
    """
    Controller for health check and utility endpoints.

    Follows Single Responsibility: Handles utility HTTP requests.
    """

    def __init__(self, mailbox_service: MailboxService):
        """
        Initialize controller with dependencies.

        Args:
            mailbox_service: Service for mailbox operations
        """
        self._mailbox_service = mailbox_service
        self._response_builder = ResponseBuilder()

    def health_check(self) -> Tuple[Any, int]:
        """
        Handle GET /health - Health check.

        Returns:
            Flask response tuple
        """
        mailbox_count = self._mailbox_service.get_mailbox_count()
        return self._response_builder.health_response(mailbox_count)

    def api_info(self) -> Tuple[Any, int]:
        """
        Handle GET / - API information.

        Returns:
            Flask response tuple
        """
        return self._response_builder.api_info_response()


def create_health_blueprint(controller: HealthController) -> Blueprint:
    """
    Create Flask blueprint for health routes.

    Args:
        controller: Health controller instance

    Returns:
        Flask blueprint
    """
    bp = Blueprint('health', __name__)

    @bp.route('/health', methods=['GET'])
    def health():
        return controller.health_check()

    @bp.route('/', methods=['GET'])
    def info():
        return controller.api_info()

    return bp
