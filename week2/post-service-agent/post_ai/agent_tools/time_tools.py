"""Date and time tools for future LLM tool-calling workflows."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Shanghai"


def get_current_time(timezone: str = DEFAULT_TIMEZONE) -> str:
    """Return the current local time for the requested IANA timezone.

    Args:
        timezone: IANA timezone name, for example "Asia/Shanghai" or "UTC".

    Returns:
        Current time formatted as HH:MM:SS.

    Raises:
        ZoneInfoNotFoundError: If the timezone name is not available on this system.
    """
    return datetime.now(ZoneInfo(timezone)).strftime("%H:%M:%S")


def get_current_date(timezone: str = DEFAULT_TIMEZONE) -> str:
    """Return the current local calendar date for the requested IANA timezone.

    Args:
        timezone: IANA timezone name, for example "Asia/Shanghai" or "UTC".

    Returns:
        Current date formatted as YYYY-MM-DD.

    Raises:
        ZoneInfoNotFoundError: If the timezone name is not available on this system.
    """
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")
