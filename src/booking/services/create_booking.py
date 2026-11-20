"""Scenario "create booking" (FR-05, docs/architecture/sequence/create-booking.mmd).

Order of checks: cheap and local first, then lookups in other contexts, then the
capacity rule. Nothing is stored and nobody is notified unless all checks pass.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from booking.domain.booking import (
    Booking,
    BookingRequested,
    CheckInInPastError,
    HostNotFoundError,
    HostUnavailableError,
    PetCardRequiredError,
    PetNotFoundError,
    StayPeriod,
    has_free_capacity,
)
from booking.ports import BookingRepository, Clock, HostDirectory, Notifier, PetCatalog


@dataclass(frozen=True, slots=True)
class CreateBookingCommand:
    """Input of the scenario. `owner_id` comes from the access token, not from the body."""

    owner_id: UUID
    host_id: UUID
    pet_id: UUID
    check_in: date
    check_out: date


class CreateBooking:
    """Use case. Dependencies are ports, passed in by the composition root."""

    def __init__(
        self,
        *,
        bookings: BookingRepository,
        hosts: HostDirectory,
        pets: PetCatalog,
        notifier: Notifier,
        clock: Clock,
    ) -> None:
        self._bookings = bookings
        self._hosts = hosts
        self._pets = pets
        self._notifier = notifier
        self._clock = clock

    async def __call__(self, command: CreateBookingCommand) -> Booking:
        """Create a booking in status `requested` and notify the host.

        Raises:
            InvalidStayPeriodError: check-out not after check-in (И-1).
            CheckInInPastError: check-in before today (AC-04.5).
            PetCardRequiredError: the owner has no pet card (AC-05.3).
            PetNotFoundError: the pet is missing or someone else's (AC-05.6).
            HostNotFoundError: the host is missing or not verified (AC-05.6).
            HostUnavailableError: the host's capacity is full on some night (AC-05.2).
        """
        period = StayPeriod(command.check_in, command.check_out)
        if period.check_in < self._clock.today():
            raise CheckInInPastError(f"Check-in {period.check_in} is in the past")

        if not await self._pets.has_any(command.owner_id):
            raise PetCardRequiredError("Create a pet card before requesting a booking")
        pet = await self._pets.snapshot(command.owner_id, command.pet_id)
        if pet is None:
            raise PetNotFoundError(f"Pet {command.pet_id} not found")

        host = await self._hosts.find_verified(command.host_id)
        if host is None:
            raise HostNotFoundError(f"Host {command.host_id} not found")

        confirmed = await self._bookings.confirmed_periods(host.host_id, period)
        if not has_free_capacity(period, host.capacity, confirmed):
            raise HostUnavailableError("The host is already booked for these dates")

        booking = Booking.request(
            booking_id=uuid4(),
            owner_id=command.owner_id,
            host_id=host.host_id,
            pet=pet,
            period=period,
            now=self._clock.now(),
        )
        await self._bookings.add(booking)
        for event in booking.pull_events():
            if isinstance(event, BookingRequested):
                await self._notifier.booking_requested(event)
        return booking
