"""Capacity rule (FR-06, ADR-0005).

Not an invariant of one booking: it needs the host's other confirmed bookings.
The rule itself is pure; the scenario loads the bookings and calls it.
"""

from collections.abc import Iterable

from booking.domain.booking.stay_period import StayPeriod


def has_free_capacity(period: StayPeriod, capacity: int, confirmed: Iterable[StayPeriod]) -> bool:
    """True if on every night of `period` fewer than `capacity` confirmed stays overlap.

    Only confirmed bookings count: a request does not hold capacity (ADR-0005).
    """
    overlapping = [other for other in confirmed if other.overlaps(period)]
    return all(
        sum(1 for other in overlapping if other.includes_night(night)) < capacity
        for night in period.each_night()
    )
