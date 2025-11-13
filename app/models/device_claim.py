"""
Device Claim Model

Represents device claims and authorization.
Follows Single Responsibility Principle: Device authorization only.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class DeviceClaim:
    """
    Device claim entity for mailbox authorization.

    Tracks which devices (sender and receiver) are authorized
    to access a specific mailbox.
    """
    mailbox_id: str
    sender_claim: str
    receiver_claim: Optional[str] = None

    def is_sender(self, device_claim: str) -> bool:
        """Check if device claim belongs to sender."""
        return self.sender_claim == device_claim

    def is_receiver(self, device_claim: str) -> bool:
        """Check if device claim belongs to receiver."""
        return self.receiver_claim == device_claim

    def is_authorized(self, device_claim: str) -> bool:
        """
        Check if device is authorized (sender or receiver).

        Args:
            device_claim: Device claim to check

        Returns:
            True if authorized, False otherwise
        """
        return device_claim in [self.sender_claim, self.receiver_claim]

    def has_receiver(self) -> bool:
        """Check if receiver is bound."""
        return self.receiver_claim is not None

    def bind_receiver(self, receiver_claim: str) -> None:
        """
        Bind receiver to mailbox.

        Args:
            receiver_claim: Receiver device claim
        """
        self.receiver_claim = receiver_claim

    def relinquish_receiver(self) -> None:
        """Relinquish receiver binding."""
        self.receiver_claim = None


class DeviceClaimRepository:
    """
    Repository for device claim data access.

    Follows Single Responsibility: Device claim persistence.
    """

    def __init__(self):
        """Initialize repository with in-memory storage."""
        self._storage: Dict[str, DeviceClaim] = {}

    def create(self, device_claim: DeviceClaim) -> DeviceClaim:
        """
        Create a new device claim.

        Args:
            device_claim: Device claim to create

        Returns:
            Created device claim
        """
        self._storage[device_claim.mailbox_id] = device_claim
        return device_claim

    def find_by_mailbox_id(self, mailbox_id: str) -> Optional[DeviceClaim]:
        """
        Find device claim by mailbox ID.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Device claim if found, None otherwise
        """
        return self._storage.get(mailbox_id)

    def find_by_sender_claim(self, sender_claim: str) -> Optional[DeviceClaim]:
        """
        Find device claim by sender claim.

        Args:
            sender_claim: Sender device claim

        Returns:
            Device claim if found, None otherwise
        """
        for claim in self._storage.values():
            if claim.sender_claim == sender_claim:
                return claim
        return None

    def update(self, device_claim: DeviceClaim) -> DeviceClaim:
        """
        Update device claim.

        Args:
            device_claim: Device claim to update

        Returns:
            Updated device claim
        """
        self._storage[device_claim.mailbox_id] = device_claim
        return device_claim

    def delete(self, mailbox_id: str) -> bool:
        """
        Delete device claim.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            True if deleted, False if not found
        """
        if mailbox_id in self._storage:
            del self._storage[mailbox_id]
            return True
        return False

    def exists(self, mailbox_id: str) -> bool:
        """
        Check if device claim exists for mailbox.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            True if exists, False otherwise
        """
        return mailbox_id in self._storage
