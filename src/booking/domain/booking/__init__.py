"""Booking context: the booking and its rules. Imports only the standard library."""

from booking.domain.booking.booking import REQUEST_TTL, Booking, BookingStatus, Cancellation
from booking.domain.booking.capacity import has_free_capacity
from booking.domain.booking.errors import (
    BookingError,
    BookingStateError,
    CheckInInPastError,
    HostNotFoundError,
    HostUnavailableError,
    InvalidStayPeriodError,
    PetCardRequiredError,
    PetNotFoundError,
)
from booking.domain.booking.events import (
    BookingCancelled,
    BookingConfirmed,
    BookingDeclined,
    BookingEvent,
    BookingRequested,
)
from booking.domain.booking.pet_snapshot import PetSnapshot, Species
from booking.domain.booking.stay_period import StayPeriod, StayPhase

__all__ = [
    "REQUEST_TTL",
    "Booking",
    "BookingCancelled",
    "BookingConfirmed",
    "BookingDeclined",
    "BookingError",
    "BookingEvent",
    "BookingRequested",
    "BookingStateError",
    "BookingStatus",
    "Cancellation",
    "CheckInInPastError",
    "HostNotFoundError",
    "HostUnavailableError",
    "InvalidStayPeriodError",
    "PetCardRequiredError",
    "PetNotFoundError",
    "PetSnapshot",
    "Species",
    "StayPeriod",
    "StayPhase",
    "has_free_capacity",
]
