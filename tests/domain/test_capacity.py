"""Capacity rule: confirmed stays per night never exceed capacity (FR-06)."""

from datetime import date

import pytest

from booking.domain.booking import StayPeriod, has_free_capacity


def period(check_in_day: int, check_out_day: int) -> StayPeriod:
    return StayPeriod(date(2026, 11, check_in_day), date(2026, 11, check_out_day))


def test_host_without_bookings_is_free() -> None:
    assert has_free_capacity(period(10, 14), capacity=1, confirmed=[])


def test_one_busy_night_makes_host_unavailable() -> None:  # AC-04.3
    assert not has_free_capacity(period(12, 16), capacity=1, confirmed=[period(10, 14)])


def test_touching_stay_does_not_block() -> None:  # AC-04.4
    assert has_free_capacity(period(14, 16), capacity=1, confirmed=[period(10, 14)])


@pytest.mark.parametrize(("capacity", "free"), [(2, False), (3, True)])
def test_capacity_boundary(capacity: int, free: bool) -> None:  # AC-06.4
    confirmed = [period(10, 14), period(11, 13)]

    assert has_free_capacity(period(12, 13), capacity, confirmed) is free


def test_occupancy_is_counted_per_night_not_per_period() -> None:
    # Two stays that do not meet: never more than one pet on the same night.
    confirmed = [period(10, 12), period(12, 14)]

    assert has_free_capacity(period(10, 14), capacity=2, confirmed=confirmed)
    assert not has_free_capacity(period(10, 14), capacity=1, confirmed=confirmed)
