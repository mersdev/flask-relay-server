"""
Mailbox Model

Represents a mailbox entity and its repository for data access.
Follows Single Responsibility Principle: Mailbox data structure and operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
import uuid


@dataclass
class MailboxConfiguration:
    """Mailbox configuration settings."""
    access_rights: str
    expiration: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            'accessRights': self.access_rights,
            'expiration': self.expiration
        }


@dataclass
class Mailbox:
    """
    Mailbox entity representing a secure credential transfer mailbox.

    Follows Single Responsibility: Represents mailbox data only.
    """
    mailbox_id: str
    payload: Dict[str, str]
    display_information: Dict[str, str]
    mailbox_configuration: MailboxConfiguration
    notification_token: Optional[Dict[str, str]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert mailbox to dictionary representation."""
        return {
            'payload': self.payload,
            'displayInformation': self.display_information,
            'notificationToken': self.notification_token,
            'mailboxConfiguration': self.mailbox_configuration.to_dict(),
            'createdAt': self.created_at
        }

    def is_expired(self) -> bool:
        """
        Check if mailbox has expired.

        Returns:
            True if expired, False otherwise
        """
        try:
            expiration_time = datetime.fromisoformat(
                self.mailbox_configuration.expiration.replace('Z', '+00:00')
            )
            return datetime.now(timezone.utc) > expiration_time
        except (ValueError, AttributeError):
            return False

    def has_access_right(self, access_type: str) -> bool:
        """
        Check if mailbox allows specific access type.

        Args:
            access_type: Type of access (R, W, or D)

        Returns:
            True if access allowed, False otherwise
        """
        return access_type in self.mailbox_configuration.access_rights

    def update_payload(self, new_payload: Dict[str, str]) -> None:
        """Update mailbox payload."""
        self.payload = new_payload

    def update_notification_token(self, token: Dict[str, str]) -> None:
        """Update notification token."""
        self.notification_token = token


class MailboxRepository:
    """
    Repository for mailbox data access.

    Follows Single Responsibility: Data persistence operations.
    Follows Dependency Inversion: Depends on abstraction (in-memory storage).
    """

    def __init__(self):
        """Initialize repository with in-memory storage."""
        self._storage: Dict[str, Mailbox] = {}

    def create(self, mailbox: Mailbox) -> Mailbox:
        """
        Create a new mailbox.

        Args:
            mailbox: Mailbox to create

        Returns:
            Created mailbox
        """
        self._storage[mailbox.mailbox_id] = mailbox
        return mailbox

    def find_by_id(self, mailbox_id: str) -> Optional[Mailbox]:
        """
        Find mailbox by ID.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            Mailbox if found, None otherwise
        """
        return self._storage.get(mailbox_id)

    def update(self, mailbox: Mailbox) -> Mailbox:
        """
        Update an existing mailbox.

        Args:
            mailbox: Mailbox to update

        Returns:
            Updated mailbox
        """
        self._storage[mailbox.mailbox_id] = mailbox
        return mailbox

    def delete(self, mailbox_id: str) -> bool:
        """
        Delete mailbox by ID.

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
        Check if mailbox exists.

        Args:
            mailbox_id: Mailbox identifier

        Returns:
            True if exists, False otherwise
        """
        return mailbox_id in self._storage

    def find_all(self) -> List[Mailbox]:
        """
        Find all mailboxes.

        Returns:
            List of all mailboxes
        """
        return list(self._storage.values())

    def find_expired(self) -> List[Mailbox]:
        """
        Find all expired mailboxes.

        Returns:
            List of expired mailboxes
        """
        return [mailbox for mailbox in self._storage.values() if mailbox.is_expired()]

    def count(self) -> int:
        """
        Get total number of mailboxes.

        Returns:
            Number of mailboxes
        """
        return len(self._storage)


def create_mailbox_from_request(
    payload: Dict[str, str],
    display_information: Dict[str, str],
    mailbox_configuration: Dict[str, str],
    notification_token: Optional[Dict[str, str]] = None
) -> Mailbox:
    """
    Factory function to create a mailbox from request data.

    Args:
        payload: Encrypted payload data
        display_information: Display information
        mailbox_configuration: Mailbox configuration
        notification_token: Optional notification token

    Returns:
        New Mailbox instance
    """
    mailbox_id = str(uuid.uuid4())
    config = MailboxConfiguration(
        access_rights=mailbox_configuration.get('accessRights', 'RD'),
        expiration=mailbox_configuration['expiration']
    )

    return Mailbox(
        mailbox_id=mailbox_id,
        payload=payload,
        display_information=display_information,
        mailbox_configuration=config,
        notification_token=notification_token
    )
