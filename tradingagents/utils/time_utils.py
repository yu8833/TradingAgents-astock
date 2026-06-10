"""Time utilities for Beijing timezone support."""

from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))


def now_beijing() -> datetime:
    """Get current time in Beijing timezone (UTC+8)."""
    return datetime.now(BEIJING_TZ)


def now_beijing_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current Beijing time as formatted string.

    Args:
        fmt: strftime format string, default "%Y-%m-%d %H:%M:%S"

    Returns:
        Formatted Beijing time string
    """
    return now_beijing().strftime(fmt)


def today_beijing() -> str:
    """Get today's date in Beijing timezone as YYYY-MM-DD string."""
    return now_beijing().strftime("%Y-%m-%d")
