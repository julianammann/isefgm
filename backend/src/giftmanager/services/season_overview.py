"""Christmas and Easter status overview (F-11)."""

from datetime import date, datetime, timedelta

from giftmanager.services.notification import local_at, local_midnight

START_DAYS = 42


def send_dates(event: date) -> list[date]:
    """Send days: the start 42 days before `event`, then every Monday before `event`."""
    start = event - timedelta(days=START_DAYS)
    days = [start]
    monday = start + timedelta(days=7 - start.weekday())
    while monday < event:
        days.append(monday)
        monday += timedelta(days=7)
    return days


def open_send(event: date, now: datetime) -> tuple[date, datetime, datetime] | None:
    """(send day, window start, window end) of the open window, or None if none is open.

    A window opens at 08:00 local time on its send day and closes at 08:00 on the next send day;
    the last one closes at local midnight on `event`.
    """
    days = send_dates(event)
    for index, send in enumerate(days):
        start = local_at(send)
        end = local_at(days[index + 1]) if index + 1 < len(days) else local_midnight(event)
        if start <= now < end:
            return send, start, end
    return None
