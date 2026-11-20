"""Storage of Booking aggregates."""

from typing import Protocol
from uuid import UUID

from booking.domain.booking import Booking, StayPeriod


class BookingRepository(Protocol):
    """A collection of bookings; how and where they are stored is not the domain's concern."""

    async def add(self, booking: Booking) -> None:
        """Store a new booking."""

    async def get(self, booking_id: UUID) -> Booking | None:
        """The booking, or None if there is no such booking."""

    async def confirmed_periods(self, host_id: UUID, overlapping: StayPeriod) -> list[StayPeriod]:
        """Periods of the host's confirmed bookings that share a night with `overlapping`.

        Input for the capacity rule (FR-06). Requests and cancelled bookings do
        not count (ADR-0005).
        """
