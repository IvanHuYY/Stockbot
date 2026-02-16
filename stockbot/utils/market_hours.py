"""Market hours utilities."""

from __future__ import annotations

from datetime import datetime, time

import exchange_calendars as xcals
import pytz

US_EASTERN = pytz.timezone("US/Eastern")
NYSE_OPEN = time(9, 30)
NYSE_CLOSE = time(16, 0)


def get_nyse_calendar():
    """Get NYSE exchange calendar."""
    return xcals.get_calendar("XNYS")


def is_market_open(dt: datetime | None = None) -> bool:
    """Check if the US stock market is currently open."""
    cal = get_nyse_calendar()
    if dt is None:
        dt = datetime.now(US_EASTERN)

    if dt.tzinfo is None:
        dt = US_EASTERN.localize(dt)

    return cal.is_open_on_minute(dt.astimezone(pytz.UTC).replace(tzinfo=None))


def next_market_open(dt: datetime | None = None) -> datetime:
    """Get the next market open time."""
    cal = get_nyse_calendar()
    if dt is None:
        dt = datetime.now(US_EASTERN)

    if dt.tzinfo is None:
        dt = US_EASTERN.localize(dt)

    ts = dt.astimezone(pytz.UTC).replace(tzinfo=None)
    next_open = cal.next_open(ts)
    return next_open.tz_localize(pytz.UTC).astimezone(US_EASTERN)


def next_market_close(dt: datetime | None = None) -> datetime:
    """Get the next market close time."""
    cal = get_nyse_calendar()
    if dt is None:
        dt = datetime.now(US_EASTERN)

    if dt.tzinfo is None:
        dt = US_EASTERN.localize(dt)

    ts = dt.astimezone(pytz.UTC).replace(tzinfo=None)
    next_close = cal.next_close(ts)
    return next_close.tz_localize(pytz.UTC).astimezone(US_EASTERN)


def get_trading_days(start: datetime, end: datetime) -> list[datetime]:
    """Get list of trading days in a date range."""
    cal = get_nyse_calendar()
    sessions = cal.sessions_in_range(start, end)
    return [s.to_pydatetime() for s in sessions]
