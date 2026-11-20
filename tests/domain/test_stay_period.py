"""StayPeriod: half-open interval of nights (И-1, AC-04.4, AC-05.4)."""

from datetime import date

import pytest

from booking.domain.booking import InvalidStayPeriodError, StayPeriod, StayPhase


def period(check_in_day: int, check_out_day: int) -> StayPeriod:
    return StayPeriod(date(2026, 11, check_in_day), date(2026, 11, check_out_day))


def test_one_night_is_the_shortest_period() -> None:  # AC-05.4
    assert period(10, 11).nights == 1


@pytest.mark.parametrize(("check_in", "check_out"), [(10, 10), (11, 10)])
def test_check_out_must_be_after_check_in(check_in: int, check_out: int) -> None:  # И-1
    with pytest.raises(InvalidStayPeriodError):
        period(check_in, check_out)


def test_nights_are_check_in_up_to_the_day_before_check_out() -> None:
    assert list(period(10, 13).each_night()) == [
        date(2026, 11, 10),
        date(2026, 11, 11),
        date(2026, 11, 12),
    ]
    assert period(10, 13).includes_night(date(2026, 11, 12))
    assert not period(10, 13).includes_night(date(2026, 11, 13))


def test_touching_periods_do_not_overlap() -> None:  # AC-04.4
    assert not period(10, 14).overlaps(period(14, 16))
    assert not period(14, 16).overlaps(period(10, 14))


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((10, 14), (12, 16)),  # AC-04.3: partly
        ((10, 14), (11, 12)),  # inside
        ((10, 14), (10, 14)),  # same dates
        ((13, 14), (10, 20)),  # around
    ],
)
def test_periods_sharing_a_night_overlap(first: tuple[int, int], second: tuple[int, int]) -> None:
    assert period(*first).overlaps(period(*second))
    assert period(*second).overlaps(period(*first))


def test_periods_with_same_dates_are_equal() -> None:
    assert period(10, 14) == period(10, 14)
    assert len({period(10, 14), period(10, 14)}) == 1


@pytest.mark.parametrize(
    ("today", "phase"),
    [
        (9, StayPhase.UPCOMING),
        (10, StayPhase.ONGOING),  # AC-09.3: on check-in day the stay is already going
        (13, StayPhase.ONGOING),
        (14, StayPhase.COMPLETED),  # check-out day
    ],
)
def test_phase_is_computed_from_dates(today: int, phase: StayPhase) -> None:
    assert period(10, 14).phase(date(2026, 11, today)) is phase
