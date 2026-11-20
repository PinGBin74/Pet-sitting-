"""Scenario "create booking": acceptance criteria of FR-05.

Doubles are shared: tests/doubles.py (stubs for clock, storage, directories;
spy for the notifier). This module only assembles the world and checks the
scenario.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from booking.domain.booking import (
    Booking,
    BookingRequested,
    BookingStatus,
    CheckInInPastError,
    HostNotFoundError,
    HostUnavailableError,
    InvalidStayPeriodError,
    PetCardRequiredError,
    PetNotFoundError,
    PetSnapshot,
    Species,
    StayPeriod,
)
from src.booking.ports import BookableHost
from src.booking.services import CreateBooking, CreateBookingCommand
from tests.doubles import (
    InMemoryBookings,
    InMemoryHosts,
    InMemoryPets,
    SpyNotifier,
    StubClock,
)

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
TODAY = NOW.date()

OWNER_ID, OTHER_OWNER_ID, HOST_ID = uuid4(), uuid4(), uuid4()
PET = PetSnapshot(
    pet_id=uuid4(),
    species=Species.DOG,
    breed="Корги",
    weight_kg=Decimal("11.5"),
    vaccinated_on=date(2026, 6, 1),
    notes="Боится пылесоса",
)


@dataclass
class World:
    bookings: InMemoryBookings
    hosts: InMemoryHosts
    pets: InMemoryPets
    notifier: SpyNotifier
    create: CreateBooking


@pytest.fixture
def world() -> World:
    bookings = InMemoryBookings(now=NOW)
    hosts = InMemoryHosts({HOST_ID: BookableHost(host_id=HOST_ID, capacity=1)})
    pets = InMemoryPets({(OWNER_ID, PET.pet_id): PET})
    notifier = SpyNotifier()
    create = CreateBooking(
        bookings=bookings, hosts=hosts, pets=pets, notifier=notifier, clock=StubClock(NOW)
    )
    return World(bookings, hosts, pets, notifier, create)


def command(
    check_in: int = 10,
    check_out: int = 14,
    *,
    owner_id: UUID = OWNER_ID,
    host_id: UUID = HOST_ID,
    pet_id: UUID = PET.pet_id,
) -> CreateBookingCommand:
    return CreateBookingCommand(
        owner_id=owner_id,
        host_id=host_id,
        pet_id=pet_id,
        check_in=date(2026, 11, check_in),
        check_out=date(2026, 11, check_out),
    )


def add_confirmed(world: World, check_in: int, check_out: int) -> None:
    other = Booking.request(
        booking_id=uuid4(),
        owner_id=OTHER_OWNER_ID,
        host_id=HOST_ID,
        pet=PET,
        period=StayPeriod(date(2026, 11, check_in), date(2026, 11, check_out)),
        now=NOW,
    )
    other.confirm(NOW)
    world.bookings.stored.append(other)


def assert_nothing_happened(world: World, stored_before: int = 0) -> None:
    assert len(world.bookings.stored) == stored_before
    assert world.notifier.requested == []


async def test_request_is_stored_and_host_notified(world: World) -> None:  # AC-05.1
    booking = await world.create(command())

    assert booking.status_at(NOW) is BookingStatus.REQUESTED
    assert booking.pet == PET
    assert booking.requested_at == NOW
    assert await world.bookings.get(booking.id) is booking
    assert world.notifier.requested == [
        BookingRequested(
            booking_id=booking.id,
            host_id=HOST_ID,
            owner_id=OWNER_ID,
            period=booking.period,
            occurred_at=NOW,
        )
    ]


async def test_host_busy_on_some_night(world: World) -> None:  # AC-05.2
    add_confirmed(world, 10, 14)

    with pytest.raises(HostUnavailableError):
        await world.create(command(12, 16))

    assert_nothing_happened(world, stored_before=1)


async def test_host_free_from_the_check_out_day_of_another_stay(world: World) -> None:  # AC-04.4
    add_confirmed(world, 10, 14)

    booking = await world.create(command(14, 16))

    assert booking.period.nights == 2


async def test_unconfirmed_requests_do_not_hold_capacity(world: World) -> None:  # ADR-0005
    await world.create(command(10, 14))

    second = await world.create(command(10, 14))

    assert second.status_at(NOW) is BookingStatus.REQUESTED
    assert len(world.bookings.stored) == 2


async def test_owner_without_pet_card(world: World) -> None:  # AC-05.3
    with pytest.raises(PetCardRequiredError):
        await world.create(command(owner_id=OTHER_OWNER_ID))

    assert_nothing_happened(world)


async def test_one_night_is_accepted(world: World) -> None:  # AC-05.4
    booking = await world.create(command(10, 11))

    assert booking.period.nights == 1


async def test_check_out_on_check_in_day_is_rejected(world: World) -> None:  # AC-05.4
    with pytest.raises(InvalidStayPeriodError):
        await world.create(command(10, 10))

    assert_nothing_happened(world)


async def test_someone_elses_pet_looks_like_a_missing_one(world: World) -> None:  # AC-05.6
    world.pets.cards[(OTHER_OWNER_ID, uuid4())] = PET

    with pytest.raises(PetNotFoundError):
        await world.create(command(owner_id=OTHER_OWNER_ID, pet_id=PET.pet_id))
    with pytest.raises(PetNotFoundError):
        await world.create(command(pet_id=uuid4()))

    assert_nothing_happened(world)


async def test_unverified_or_missing_host(world: World) -> None:  # AC-05.6
    with pytest.raises(HostNotFoundError):
        await world.create(command(host_id=uuid4()))

    assert_nothing_happened(world)


async def test_check_in_today_is_allowed(world: World) -> None:  # AC-04.5 boundary
    booking = await world.create(command(1, 3))

    assert booking.period.check_in == TODAY


async def test_check_in_in_the_past_is_rejected(world: World) -> None:  # AC-04.5
    past = CreateBookingCommand(
        owner_id=OWNER_ID,
        host_id=HOST_ID,
        pet_id=PET.pet_id,
        check_in=date(2026, 10, 31),
        check_out=date(2026, 11, 2),
    )

    with pytest.raises(CheckInInPastError):
        await world.create(past)

    assert_nothing_happened(world)
