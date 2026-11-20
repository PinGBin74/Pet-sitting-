"""StayPeriod: the nights a pet stays with the host."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from booking.domain.booking.errors import InvalidStayPeriodError


class StayPhase(StrEnum):
    """Phase of a confirmed stay. Computed from the dates, never stored."""

    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class StayPeriod:
    """Half-open interval of nights [check_in, check_out).

    A value object: two periods with the same dates are equal. The night of
    check-out is not included, so check-out on the 14th and check-in on the 14th
    do not overlap (AC-04.4).
    """

    check_in: date
    check_out: date

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:  # И-1
            raise InvalidStayPeriodError(
                f"Check-out {self.check_out} must be after check-in {self.check_in}"
            )

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    def each_night(self) -> Iterator[date]:
        """Dates of the nights: check-in date up to the day before check-out."""
        for offset in range(self.nights):
            yield self.check_in + timedelta(days=offset)

    def includes_night(self, night: date) -> bool:
        return self.check_in <= night < self.check_out

    def overlaps(self, other: "StayPeriod") -> bool:
        """True if the periods share at least one night."""
        return self.check_in < other.check_out and other.check_in < self.check_out

    def phase(self, today: date) -> StayPhase:
        """The stay starts on the check-in day and is over on the check-out day."""
        if today < self.check_in:
            return StayPhase.UPCOMING
        if today < self.check_out:
            return StayPhase.ONGOING
        return StayPhase.COMPLETED
