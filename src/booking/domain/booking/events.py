"""Domain events of the Booking aggregate (docs/domain/aggregates.md, «События»).

Events carry identifiers and dates only: no names, contacts or addresses.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from booking.domain.booking.stay_period import StayPeriod


@dataclass(frozen=True, slots=True)
class BookingRequested:
    booking_id: UUID
    host_id: UUID
    owner_id: UUID
    period: StayPeriod
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class BookingConfirmed:
    booking_id: UUID
    host_id: UUID
    owner_id: UUID
    period: StayPeriod
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class BookingDeclined:
    booking_id: UUID
    owner_id: UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class BookingCancelled:
    booking_id: UUID
    host_id: UUID
    occurred_at: datetime


type BookingEvent = BookingRequested | BookingConfirmed | BookingDeclined | BookingCancelled
