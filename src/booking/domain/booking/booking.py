"""Booking: the main aggregate of the Booking context (docs/domain/aggregates.md)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from booking.domain.booking.errors import BookingStateError
from booking.domain.booking.events import (
    BookingCancelled,
    BookingConfirmed,
    BookingDeclined,
    BookingEvent,
    BookingRequested,
)
from booking.domain.booking.pet_snapshot import PetSnapshot
from booking.domain.booking.stay_period import StayPeriod

# FR-13: a request without the host's answer expires after this time.
REQUEST_TTL = timedelta(hours=48)


class BookingStatus(StrEnum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Cancellation:
    """Who cancelled, when, and why (the reason is optional)."""

    cancelled_by: UUID
    cancelled_at: datetime
    reason: str | None = None


class Booking:
    """Aggregate root. State changes only through its methods.

    Time is always passed in (`now`): the aggregate never reads the clock, so its
    rules are checked by tests without waiting or patching.

    Not an invariant and therefore checked elsewhere: the host's capacity
    (needs other bookings), the host being verified and the pet belonging to the
    owner (other contexts), check-in not in the past (needs today's date).
    """

    def __init__(
        self,
        *,
        booking_id: UUID,
        owner_id: UUID,
        host_id: UUID,
        pet: PetSnapshot,
        period: StayPeriod,
        status: BookingStatus,
        requested_at: datetime,
        decided_at: datetime | None = None,
        cancellation: Cancellation | None = None,
    ) -> None:
        """Restore a booking as stored. A new booking is made by `Booking.request`."""
        self._id = booking_id
        self._owner_id = owner_id
        self._host_id = host_id
        self._pet = pet  # И-4: a booking always has a pet snapshot
        self._period = period
        self._status = status
        self._requested_at = requested_at
        self._decided_at = decided_at
        self._cancellation = cancellation
        self._events: list[BookingEvent] = []

    @classmethod
    def request(
        cls,
        *,
        booking_id: UUID,
        owner_id: UUID,
        host_id: UUID,
        pet: PetSnapshot,
        period: StayPeriod,
        now: datetime,
    ) -> "Booking":
        """Factory: the only way a booking comes into existence (FR-05)."""
        booking = cls(
            booking_id=booking_id,
            owner_id=owner_id,
            host_id=host_id,
            pet=pet,
            period=period,
            status=BookingStatus.REQUESTED,
            requested_at=now,
        )
        booking._events.append(
            BookingRequested(
                booking_id=booking_id,
                host_id=host_id,
                owner_id=owner_id,
                period=period,
                occurred_at=now,
            )
        )
        return booking

    # --- Reading ------------------------------------------------------------------

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def host_id(self) -> UUID:
        return self._host_id

    @property
    def pet(self) -> PetSnapshot:
        return self._pet

    @property
    def period(self) -> StayPeriod:
        return self._period

    @property
    def requested_at(self) -> datetime:
        return self._requested_at

    @property
    def decided_at(self) -> datetime | None:
        return self._decided_at

    @property
    def cancellation(self) -> Cancellation | None:
        return self._cancellation

    @property
    def expires_at(self) -> datetime:
        return self._requested_at + REQUEST_TTL

    @property
    def stored_status(self) -> BookingStatus:
        """Status as written; expiry is not applied. For storage, not for decisions."""
        return self._status

    def status_at(self, now: datetime) -> BookingStatus:
        """Status at the moment `now`. Expiry is computed on read, not stored (FR-13)."""
        if self._status is BookingStatus.REQUESTED and now >= self.expires_at:
            return BookingStatus.EXPIRED  # AC-13.2: at exactly 48 h it has expired
        return self._status

    # --- Commands -----------------------------------------------------------------

    def confirm(self, now: datetime) -> None:
        """Host accepts the request (FR-06). Capacity is checked by the scenario."""
        self._ensure_requested(now, "confirm")
        self._status = BookingStatus.CONFIRMED
        self._decided_at = now
        self._events.append(
            BookingConfirmed(
                booking_id=self._id,
                host_id=self._host_id,
                owner_id=self._owner_id,
                period=self._period,
                occurred_at=now,
            )
        )

    def decline(self, now: datetime) -> None:
        """Host rejects the request (FR-06)."""
        self._ensure_requested(now, "decline")
        self._status = BookingStatus.DECLINED
        self._decided_at = now
        self._events.append(
            BookingDeclined(booking_id=self._id, owner_id=self._owner_id, occurred_at=now)
        )

    def cancel(self, *, by: UUID, now: datetime, reason: str | None = None) -> None:
        """Owner cancels (FR-09). И-3: repeated cancellation changes nothing (AC-09.4)."""
        status = self.status_at(now)
        if status is BookingStatus.CANCELLED:
            return
        if status not in (BookingStatus.REQUESTED, BookingStatus.CONFIRMED):
            raise BookingStateError(self._id, status, "cancel")
        self._status = BookingStatus.CANCELLED
        self._cancellation = Cancellation(cancelled_by=by, cancelled_at=now, reason=reason)
        self._events.append(
            BookingCancelled(booking_id=self._id, host_id=self._host_id, occurred_at=now)
        )

    def pull_events(self) -> list[BookingEvent]:
        """Hand over the recorded events once; the scenario publishes them."""
        events, self._events = self._events, []
        return events

    def _ensure_requested(self, now: datetime, action: str) -> None:
        status = self.status_at(now)
        if status is not BookingStatus.REQUESTED:  # И-2, AC-13.3
            raise BookingStateError(self._id, status, action)

    # --- Identity -----------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Booking) and other._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Booking(id={self._id}, status={self._status.value}, period={self._period})"
