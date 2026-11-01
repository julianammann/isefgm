"""Injectable time source."""

from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated, Protocol
from zoneinfo import ZoneInfo

from fastapi import Depends

from giftmanager.core.config import get_settings


class Clock(Protocol):
    """Injected time source so tests and the scheduler can pin `now`."""

    def now(self) -> datetime:
        """Return the current time, timezone-aware in UTC."""
        ...


class SystemClock:
    """Production clock backed by the system time."""

    def now(self) -> datetime:
        """Return `datetime.now(UTC)`."""
        return datetime.now(UTC)


@lru_cache
def get_clock() -> Clock:
    """FastAPI dependency; tests override it with a fixed clock."""
    return SystemClock()


def local_today(clock: Clock) -> date:
    """Calendar date of the clock's now in the app time zone."""
    return clock.now().astimezone(ZoneInfo(get_settings().default_timezone)).date()


ClockDep = Annotated[Clock, Depends(get_clock)]
