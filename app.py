"""
Main Application Entry Point

Starts the Flask Relay Server using the application factory pattern.
Follows SOLID principles with proper separation of concerns.
"""

import logging
from app import create_app
from app.config import AppConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create application using factory
app = create_app()

if __name__ == '__main__':
    logger.info("="*60)
    logger.info(f"🚀 Starting {AppConfig.SERVICE_NAME}")
    logger.info(f"📡 Server will be available at http://{AppConfig.DEFAULT_HOST}:{AppConfig.DEFAULT_PORT}")
    logger.info(f"📋 API Version: {AppConfig.API_VERSION}")
    logger.info(f"📖 Specification: {AppConfig.SPECIFICATION}")
    logger.info("="*60)

    app.run(
        host=AppConfig.DEFAULT_HOST,
        port=AppConfig.DEFAULT_PORT,
        debug=AppConfig.DEBUG
    )
