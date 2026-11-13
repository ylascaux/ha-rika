"""Heating time ranges of the weekly schedule.

The cloud holds each range as "HHMMHHMM" (start then end); "00000000" means
no range. Here a range is written "HH:MM-HH:MM" and no range is "".
"""

from __future__ import annotations

import re

EMPTY = "00000000"

TEXT_PATTERN = r"^$|^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$"

_TEXT = re.compile(r"^(\d\d):(\d\d)-(\d\d):(\d\d)$")
_RAW = re.compile(r"^\d{8}$")


def decode(raw: str | None) -> str | None:
    """Turn "06000830" into "06:00-08:30"; None when the value is not a range."""
    if raw is None or not _RAW.match(str(raw)):
        return None
    if raw == EMPTY:
        return ""
    return f"{raw[0:2]}:{raw[2:4]}-{raw[4:6]}:{raw[6:8]}"


def encode(text: str) -> str:
    """Turn "06:00-08:30" into "06000830"; raise ValueError on a bad range."""
    text = text.strip()
    if not text:
        return EMPTY
    match = _TEXT.match(text)
    if not match:
        raise ValueError("format")
    start_h, start_m, end_h, end_m = (int(part) for part in match.groups())
    if start_h > 23 or end_h > 23 or start_m > 59 or end_m > 59:
        raise ValueError("format")
    if (end_h, end_m) <= (start_h, start_m):
        raise ValueError("order")
    return f"{start_h:02d}{start_m:02d}{end_h:02d}{end_m:02d}"
