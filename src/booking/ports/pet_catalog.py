"""Pet cards from the Members context, as seen by Booking."""

from typing import Protocol
from uuid import UUID

from booking.domain.booking import PetSnapshot


class PetCatalog(Protocol):
    async def has_any(self, owner_id: UUID) -> bool:
        """True if the owner has at least one pet card (AC-05.3)."""

    async def snapshot(self, owner_id: UUID, pet_id: UUID) -> PetSnapshot | None:
        """A copy of the owner's pet card; None if missing or someone else's (AC-05.6)."""
