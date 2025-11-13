"""
Mailbox Service

Business logic for mailbox operations.
Follows Single Responsibility: Mailbox business logic only.
Follows Dependency Inversion: Depends on repository abstractions.
"""

from typing import Dict, Optional, List, Any
import logging

from app.models.mailbox import Mailbox, MailboxRepository, create_mailbox_from_request
from app.models.device_claim import DeviceClaim, DeviceClaimRepository
from app.config import AccessRights

logger = logging.getLogger(__name__)


class MailboxService:
    """
    Service for mailbox business logic.

    Follows Single Responsibility: Coordinates mailbox operations.
    Follows Dependency Inversion: Depends on repository interfaces.
    """

    def __init__(
        self,
        mailbox_repository: MailboxRepository,
        device_claim_repository: DeviceClaimRepository
    ):
        """
        Initialize service with dependencies.

        Args:
            mailbox_repository: Repository for mailbox data
            device_claim_repository: Repository for device claim data
        """
        self._mailbox_repo = mailbox_repository
        self._device_claim_repo = device_claim_repository

    def create_mailbox(
        self,
        payload: Dict[str, str],
        display_information: Dict[str, str],
        mailbox_configuration: Dict[str, str],
        sender_device_claim: str,
        notification_token: Optional[Dict[str, str]] = None
    ) -> Mailbox:
        """
        Create a new mailbox.

        Args:
            payload: Encrypted payload
            display_information: Display information
            mailbox_configuration: Mailbox configuration
            sender_device_claim: Sender's device claim
            notification_token: Optional notification token

        Returns:
            Created mailbox
        """
        # Create mailbox
        mailbox = create_mailbox_from_request(
            payload=payload,
            display_information=display_information,
            mailbox_configuration=mailbox_configuration,
            notification_token=notification_token
        )

        # Save mailbox
        mailbox = self._mailbox_repo.create(mailbox)

        # Create device claim binding
        device_claim = DeviceClaim(
            mailbox_id=mailbox.mailbox_id,
            sender_claim=sender_device_claim,
            receiver_claim=None
        )
        self._device_claim_repo.create(device_claim)

        logger.info(f"Created mailbox {mailbox.mailbox_id} for device {sender_device_claim[:8]}...")

        return mailbox

    def find_mailbox(self, mailbox_id: str) -> Optional[Mailbox]:
        """
        Find mailbox by ID.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Mailbox if found, None otherwise
        """
        return self._mailbox_repo.find_by_id(mailbox_id)

    def update_mailbox_payload(
        self,
        mailbox_id: str,
        new_payload: Dict[str, str],
        notification_token: Optional[Dict[str, str]] = None
    ) -> Mailbox:
        """
        Update mailbox payload.

        Args:
            mailbox_id: Mailbox identifier
            new_payload: New payload
            notification_token: Optional notification token

        Returns:
            Updated mailbox

        Raises:
            ValueError: If mailbox not found
        """
        mailbox = self._mailbox_repo.find_by_id(mailbox_id)
        if not mailbox:
            raise ValueError(f"Mailbox {mailbox_id} not found")

        mailbox.update_payload(new_payload)

        if notification_token:
            mailbox.update_notification_token(notification_token)

        return self._mailbox_repo.update(mailbox)

    def delete_mailbox(self, mailbox_id: str) -> bool:
        """
        Delete mailbox and associated device claims.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            True if deleted, False if not found
        """
        mailbox_deleted = self._mailbox_repo.delete(mailbox_id)
        self._device_claim_repo.delete(mailbox_id)

        if mailbox_deleted:
            logger.info(f"Deleted mailbox {mailbox_id}")

        return mailbox_deleted

    def is_device_authorized(self, mailbox_id: str, device_claim: str) -> bool:
        """
        Check if device is authorized to access mailbox.

        Args:
            mailbox_id: Mailbox identifier
            device_claim: Device claim

        Returns:
            True if authorized, False otherwise
        """
        claims = self._device_claim_repo.find_by_mailbox_id(mailbox_id)
        if not claims:
            return False

        return claims.is_authorized(device_claim)

    def bind_receiver_if_needed(
        self,
        mailbox_id: str,
        device_claim: str
    ) -> bool:
        """
        Bind receiver to mailbox if not already bound.

        Args:
            mailbox_id: Mailbox identifier
            device_claim: Device claim

        Returns:
            True if receiver was bound, False if already bound or is sender
        """
        claims = self._device_claim_repo.find_by_mailbox_id(mailbox_id)
        if not claims:
            return False

        # If receiver not yet bound and this is not the sender
        if not claims.has_receiver() and not claims.is_sender(device_claim):
            claims.bind_receiver(device_claim)
            self._device_claim_repo.update(claims)
            logger.info(f"Bound receiver {device_claim[:8]}... to mailbox {mailbox_id}")
            return True

        return False

    def relinquish_receiver(self, mailbox_id: str, device_claim: str) -> bool:
        """
        Relinquish receiver binding from mailbox.

        Args:
            mailbox_id: Mailbox identifier
            device_claim: Device claim

        Returns:
            True if relinquished, False if not receiver

        Raises:
            ValueError: If device is not the receiver
        """
        claims = self._device_claim_repo.find_by_mailbox_id(mailbox_id)
        if not claims:
            raise ValueError(f"Mailbox {mailbox_id} not found")

        if not claims.is_receiver(device_claim):
            raise ValueError("Only receiver can relinquish mailbox")

        claims.relinquish_receiver()
        self._device_claim_repo.update(claims)

        logger.info(f"Device {device_claim[:8]}... relinquished mailbox {mailbox_id}")

        return True

    def has_access_right(self, mailbox_id: str, access_type: str) -> bool:
        """
        Check if mailbox allows specific access type.

        Args:
            mailbox_id: Mailbox identifier
            access_type: Type of access (R, W, or D)

        Returns:
            True if access allowed, False otherwise
        """
        mailbox = self._mailbox_repo.find_by_id(mailbox_id)
        if not mailbox:
            return False

        return mailbox.has_access_right(access_type)

    def cleanup_expired_mailboxes(self) -> int:
        """
        Remove all expired mailboxes.

        Returns:
            Number of mailboxes cleaned up
        """
        expired_mailboxes = self._mailbox_repo.find_expired()

        count = 0
        for mailbox in expired_mailboxes:
            if self.delete_mailbox(mailbox.mailbox_id):
                count += 1
                logger.info(f"Cleaned up expired mailbox: {mailbox.mailbox_id}")

        return count

    def get_mailbox_count(self) -> int:
        """
        Get total number of mailboxes.

        Returns:
            Number of mailboxes
        """
        return self._mailbox_repo.count()

    def find_mailbox_by_sender_claim(self, sender_claim: str) -> Optional[Mailbox]:
        """
        Find mailbox by sender device claim.

        Args:
            sender_claim: Sender device claim

        Returns:
            Mailbox if found, None otherwise
        """
        device_claim = self._device_claim_repo.find_by_sender_claim(sender_claim)
        if not device_claim:
            return None

        return self._mailbox_repo.find_by_id(device_claim.mailbox_id)
