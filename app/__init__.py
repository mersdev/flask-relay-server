"""
Application Package

Flask application factory following MVC pattern and SOLID principles.
"""

from flask import Flask
import logging

from app.config import AppConfig, SecurityHeaders
from app.models import MailboxRepository, DeviceClaimRepository
from app.services import MailboxService, ValidationService, DeduplicationService
from app.controllers import MailboxController, HealthController
from app.controllers.mailbox_controller import create_mailbox_blueprint
from app.controllers.health_controller import create_health_blueprint


def create_app() -> Flask:
    """
    Application factory function.

    Creates and configures the Flask application following SOLID principles:
    - Single Responsibility: Each component has one clear purpose
    - Open/Closed: Easy to extend without modifying existing code
    - Liskov Substitution: Repositories and services are interchangeable
    - Interface Segregation: Controllers depend only on what they need
    - Dependency Inversion: Depend on abstractions (services), not concrete implementations

    Returns:
        Configured Flask application
    """
    # Create Flask app
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # ========================================
    # Dependency Injection Container
    # ========================================

    # Create repositories (Data Layer)
    mailbox_repository = MailboxRepository()
    device_claim_repository = DeviceClaimRepository()

    # Create services (Business Logic Layer)
    mailbox_service = MailboxService(mailbox_repository, device_claim_repository)
    validation_service = ValidationService()
    deduplication_service = DeduplicationService()

    # Create controllers (Presentation Layer)
    mailbox_controller = MailboxController(
        mailbox_service,
        validation_service,
        deduplication_service
    )
    health_controller = HealthController(mailbox_service)

    # ========================================
    # Register Blueprints
    # ========================================

    app.register_blueprint(create_mailbox_blueprint(mailbox_controller))
    app.register_blueprint(create_health_blueprint(health_controller))

    # ========================================
    # Middleware
    # ========================================

    @app.before_request
    def before_request_handler():
        """Execute before each request to cleanup expired mailboxes."""
        cleaned = mailbox_service.cleanup_expired_mailboxes()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired mailbox(es)")

    @app.after_request
    def after_request_handler(response):
        """Execute after each request to add security headers."""
        for header_name, header_value in SecurityHeaders.HEADERS.items():
            response.headers[header_name] = header_value
        return response

    # ========================================
    # Log Application Startup
    # ========================================

    logger.info(f"Starting {AppConfig.SERVICE_NAME}")
    logger.info(f"API Version: {AppConfig.API_VERSION}")
    logger.info(f"Specification: {AppConfig.SPECIFICATION}")

    return app
