"""Совместно используемые тестовые двойники"""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from src.booking.domain.booking import (
    Booking,
    BookingRequested,
    BookingStatus,
    PetSnapshot,
    StayPeriod,
)
from src.booking.ports import BookableHost


@dataclass
class StubClock:
    """возвращает фиксированное время"""

    fixed_now: datetime
    fixed_today: date | None = None

    def now(self) -> datetime:
        return self.fixed_now

    def today(self) -> date:
        return self.fixed_today or self.fixed_now.date()


@dataclass
class InMemoryBookings:
    """записи o бронировании"""

    stored: list[Booking] = field(default_factory=list)
    now: datetime | None = None

    async def add(self, booking: Booking) -> None:
        self.stored.append(booking)

    async def get(self, booking_id: UUID) -> Booking | None:
        return next((b for b in self.stored if b.id == booking_id), None)

    async def confirmed_periods(self, host_id: UUID, overlapping: StayPeriod) -> list[StayPeriod]:
        moment = self.now or datetime.now()
        return [
            b.period
            for b in self.stored
            if b.host_id == host_id
            and b.status_at(moment) is BookingStatus.CONFIRMED
            and b.period.overlaps(overlapping)
        ]


@dataclass
class InMemoryHosts:
    """каталог верифицированных содержателей"""

    verified: dict[UUID, BookableHost] = field(default_factory=dict)

    async def find_verified(self, host_id: UUID) -> BookableHost | None:
        return self.verified.get(host_id)


@dataclass
class InMemoryPets:
    """каталог животных"""

    cards: dict[tuple[UUID, UUID], PetSnapshot] = field(default_factory=dict)

    async def has_any(self, owner_id: UUID) -> bool:
        return any(owner == owner_id for owner, _ in self.cards)

    async def snapshot(self, owner_id: UUID, pet_id: UUID) -> PetSnapshot | None:
        return self.cards.get((owner_id, pet_id))


@dataclass
class SpyNotifier:
    """шпиониро"""

    requested: list[BookingRequested] = field(default_factory=list)

    async def booking_requested(self, event: BookingRequested) -> None:
        self.requested.append(event)
