"""Current time. Scenarios read it here and pass it to the domain."""

from datetime import date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current moment, timezone-aware."""

    def today(self) -> date:
        """Current date in the service's time zone: decides 'check-in not in the past'."""
