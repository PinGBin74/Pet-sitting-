"""Rule violations of the Booking context.

The HTTP layer maps them to responses; the domain knows nothing about HTTP.
Suggested mapping is noted for each error (docs/api/resources.md).
"""

from uuid import UUID


class BookingError(Exception):
    """Base class: a booking rule is violated."""


# --- Invariants of the aggregate -------------------------------------------------


class InvalidStayPeriodError(BookingError):
    """И-1: check-out must be after check-in, at least one night (AC-04.6, AC-05.4). → 422"""


class BookingStateError(BookingError):
    """И-2, И-3, AC-13.3: the action is not allowed in the current status. → 409"""

    def __init__(self, booking_id: UUID, status: str, action: str) -> None:
        super().__init__(f"Cannot {action} booking {booking_id} in status {status!r}")
        self.booking_id = booking_id
        self.status = status
        self.action = action


# --- Rules of the "create booking" scenario --------------------------------------


class CheckInInPastError(BookingError):
    """Check-in earlier than today; today itself is allowed (AC-04.5). → 422"""


class PetCardRequiredError(BookingError):
    """The owner has no pet card at all (AC-05.3). → 422"""


class PetNotFoundError(BookingError):
    """The pet does not exist or belongs to someone else (AC-05.6, NFR-02). → 404

    One error for both cases: the answer must not reveal that a foreign pet exists.
    """


class HostNotFoundError(BookingError):
    """The host does not exist or is not verified (AC-05.6, AC-04.7, NFR-02). → 404"""


class HostUnavailableError(BookingError):
    """Confirmed bookings already fill the host's capacity on some night (AC-05.2). → 409"""
