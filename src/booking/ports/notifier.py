"""Notifications to the parties: anti-corruption layer before the mail server.

Methods speak the domain's language. Subjects, addresses and the delivery
channel belong to the implementation; by C-06 the first one writes to the log.
"""

from typing import Protocol

from booking.domain.booking import BookingRequested


class Notifier(Protocol):
    async def booking_requested(self, event: BookingRequested) -> None:
        """Tell the host about a new request (AC-05.1)."""
