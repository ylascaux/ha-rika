"""Weekly heating times of the stove, copied from a Home Assistant schedule.

The stove takes two time ranges a day. The cloud holds each one as
"HHMMHHMM" (start then end); "00000000" means the range is not used.
"""

from __future__ import annotations

from datetime import time
from typing import Any

EMPTY = "00000000"

RANGES_PER_DAY = 2

# Home Assistant's name of each weekday, and the one in the stove's controls
DAYS = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}


class TooManyRanges(Exception):
    """A day of the schedule has more ranges than the stove takes."""


def _minutes(value: Any) -> int:
    """Read a time of the schedule, given as a time or as "HH:MM:SS"."""
    if not isinstance(value, time):
        value = time.fromisoformat(str(value))
    return value.hour * 60 + value.minute


def from_schedule(plan: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    """Turn the week of a Home Assistant schedule into the stove's controls."""
    controls: dict[str, str] = {}
    for day, short in DAYS.items():
        ranges = sorted(
            (start, end)
            for start, end in (
                (_minutes(block["from"]), _minutes(block["to"]))
                for block in plan.get(day, [])
            )
            # A range shorter than a minute cannot be told to the stove.
            if end > start
        )
        if len(ranges) > RANGES_PER_DAY:
            raise TooManyRanges(day)
        for slot in range(RANGES_PER_DAY):
            raw = EMPTY
            if slot < len(ranges):
                start, end = ranges[slot]
                raw = f"{start // 60:02d}{start % 60:02d}{end // 60:02d}{end % 60:02d}"
            controls[f"heatingTime{short}{slot + 1}"] = raw
    return controls
