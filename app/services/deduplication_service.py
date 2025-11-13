"""
Deduplication Service

Request deduplication logic.
Follows Single Responsibility: Request tracking only.
"""

from typing import Dict, Optional


class DeduplicationService:
    """
    Service for request deduplication.

    Follows Single Responsibility: Tracks processed requests.
    """

    def __init__(self):
        """Initialize service with in-memory storage."""
        self._processed_requests: Dict[str, str] = {}

    def is_duplicate_request(self, device_claim: str, request_id: str) -> bool:
        """
        Check if request is a duplicate.

        Args:
            device_claim: Device claim UUID
            request_id: Request ID UUID

        Returns:
            True if duplicate, False otherwise
        """
        return (device_claim in self._processed_requests and
                self._processed_requests[device_claim] == request_id)

    def mark_request_processed(self, device_claim: str, request_id: str) -> None:
        """
        Mark request as processed.

        Args:
            device_claim: Device claim UUID
            request_id: Request ID UUID
        """
        self._processed_requests[device_claim] = request_id

    def get_last_request_id(self, device_claim: str) -> Optional[str]:
        """
        Get last processed request ID for device.

        Args:
            device_claim: Device claim UUID

        Returns:
            Last request ID if exists, None otherwise
        """
        return self._processed_requests.get(device_claim)
