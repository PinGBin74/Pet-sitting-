"""What the Booking context needs to know about a host."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BookableHost:
    """A host as Booking sees it: identifier and capacity, already verified.

    Moderation details stay in the Hosts context (docs/domain/event-storming.md).
    """

    host_id: UUID
    capacity: int


class HostDirectory(Protocol):
    async def find_verified(self, host_id: UUID) -> BookableHost | None:
        """The host if it exists and is approved by a moderator; otherwise None.

        Missing and unverified hosts look the same to the caller (NFR-02).
        """
