"""Booking aggregate: creation, transitions, expiry (И-2, И-3, И-4, FR-13)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from booking.domain.booking import (
    REQUEST_TTL,
    Booking,
    BookingCancelled,
    BookingConfirmed,
    BookingDeclined,
    BookingRequested,
    BookingStateError,
    BookingStatus,
    PetSnapshot,
    Species,
    StayPeriod,
)

REQUESTED_AT = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
OWNER_ID = uuid4()
HOST_ID = uuid4()
PET = PetSnapshot(
    pet_id=uuid4(),
    species=Species.CAT,
    breed="Сибирская",
    weight_kg=Decimal("4.2"),
    vaccinated_on=date(2026, 5, 1),
)
PERIOD = StayPeriod(date(2026, 11, 20), date(2026, 11, 24))


def new_booking() -> Booking:
    return Booking.request(
        booking_id=uuid4(),
        owner_id=OWNER_ID,
        host_id=HOST_ID,
        pet=PET,
        period=PERIOD,
        now=REQUESTED_AT,
    )


def later(**delta: float) -> datetime:
    return REQUESTED_AT + timedelta(**delta)


def test_request_creates_booking_waiting_for_host() -> None:
    booking = new_booking()

    assert booking.status_at(REQUESTED_AT) is BookingStatus.REQUESTED
    assert booking.pet == PET  # И-4: snapshot travels with the booking
    assert booking.owner_id == OWNER_ID
    assert booking.host_id == HOST_ID
    assert booking.period == PERIOD
    assert booking.requested_at == REQUESTED_AT
    assert booking.decided_at is None
    assert booking.cancellation is None
    assert booking.pull_events() == [
        BookingRequested(
            booking_id=booking.id,
            host_id=HOST_ID,
            owner_id=OWNER_ID,
            period=PERIOD,
            occurred_at=REQUESTED_AT,
        )
    ]


def test_events_are_handed_over_once() -> None:
    booking = new_booking()

    booking.pull_events()

    assert booking.pull_events() == []


def test_host_confirms_request() -> None:
    booking = new_booking()
    booking.pull_events()

    booking.confirm(later(hours=1))

    assert booking.status_at(later(hours=1)) is BookingStatus.CONFIRMED
    assert booking.decided_at == later(hours=1)
    assert [type(e) for e in booking.pull_events()] == [BookingConfirmed]


def test_host_declines_request() -> None:
    booking = new_booking()
    booking.pull_events()

    booking.decline(later(hours=1))

    assert booking.status_at(later(hours=1)) is BookingStatus.DECLINED
    assert [type(e) for e in booking.pull_events()] == [BookingDeclined]


@pytest.mark.parametrize("first", ["confirm", "decline"])
@pytest.mark.parametrize("second", ["confirm", "decline"])
def test_decision_only_on_requested_booking(first: str, second: str) -> None:  # И-2, AC-06.6
    booking = new_booking()
    getattr(booking, first)(later(hours=1))

    with pytest.raises(BookingStateError) as error:
        getattr(booking, second)(later(hours=2))

    assert error.value.action == second


@pytest.mark.parametrize("decide", ["confirm", "decline"])
def test_decision_one_minute_before_expiry_is_accepted(decide: str) -> None:  # AC-13.2
    booking = new_booking()

    getattr(booking, decide)(later(hours=47, minutes=59))

    assert booking.decided_at == later(hours=47, minutes=59)


@pytest.mark.parametrize("decide", ["confirm", "decline"])
def test_decision_at_exactly_48_hours_is_rejected(decide: str) -> None:  # AC-13.2, AC-13.3
    booking = new_booking()

    with pytest.raises(BookingStateError) as error:
        getattr(booking, decide)(later(hours=48))

    assert error.value.status == BookingStatus.EXPIRED


def test_request_expires_on_read_without_being_stored() -> None:  # AC-13.1
    booking = new_booking()

    assert booking.expires_at == REQUESTED_AT + REQUEST_TTL
    assert booking.status_at(later(hours=48, minutes=1)) is BookingStatus.EXPIRED
    assert booking.stored_status is BookingStatus.REQUESTED


def test_confirmed_booking_never_expires() -> None:
    booking = new_booking()
    booking.confirm(later(hours=1))

    assert booking.status_at(later(days=30)) is BookingStatus.CONFIRMED


@pytest.mark.parametrize("before", [None, "confirm"])
def test_owner_cancels_request_or_confirmed_booking(before: str | None) -> None:  # AC-09.1/5
    booking = new_booking()
    if before:
        getattr(booking, before)(later(hours=1))
    booking.pull_events()

    booking.cancel(by=OWNER_ID, now=later(hours=2), reason="Поездка отменилась")

    assert booking.status_at(later(hours=2)) is BookingStatus.CANCELLED
    assert booking.cancellation is not None
    assert booking.cancellation.cancelled_by == OWNER_ID
    assert booking.cancellation.reason == "Поездка отменилась"
    assert booking.pull_events() == [
        BookingCancelled(booking_id=booking.id, host_id=HOST_ID, occurred_at=later(hours=2))
    ]


def test_second_cancellation_changes_nothing() -> None:  # И-3, AC-09.4
    booking = new_booking()
    booking.cancel(by=OWNER_ID, now=later(hours=1))
    booking.pull_events()
    first = booking.cancellation

    booking.cancel(by=OWNER_ID, now=later(hours=2))

    assert booking.cancellation == first
    assert booking.pull_events() == []


def test_cancelled_request_does_not_expire() -> None:  # AC-13.4
    booking = new_booking()
    booking.cancel(by=OWNER_ID, now=later(hours=1))

    assert booking.status_at(later(hours=72)) is BookingStatus.CANCELLED


@pytest.mark.parametrize(
    ("prepare", "moment"),
    [
        ("decline", later(hours=2)),
        (None, later(hours=48)),  # expired
    ],
)
def test_cannot_cancel_declined_or_expired(prepare: str | None, moment: datetime) -> None:
    booking = new_booking()
    if prepare:
        getattr(booking, prepare)(later(hours=1))

    with pytest.raises(BookingStateError):
        booking.cancel(by=OWNER_ID, now=moment)


def test_bookings_are_equal_by_identity_only() -> None:
    booking = new_booking()
    restored = Booking(
        booking_id=booking.id,
        owner_id=OWNER_ID,
        host_id=HOST_ID,
        pet=PET,
        period=PERIOD,
        status=BookingStatus.CONFIRMED,
        requested_at=REQUESTED_AT,
    )

    assert booking == restored
    assert hash(booking) == hash(restored)
    assert booking != new_booking()
    assert booking != booking.id
    assert str(booking.id) in repr(booking)
