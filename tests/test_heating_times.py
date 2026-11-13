"""Tests of the heating time ranges."""

import pytest

from custom_components.rika import heating_times


def test_decode():
    assert heating_times.decode("06000830") == "06:00-08:30"
    assert heating_times.decode("00000000") == ""
    assert heating_times.decode(None) is None
    assert heating_times.decode("abc") is None


def test_encode():
    assert heating_times.encode("06:00-08:30") == "06000830"
    assert heating_times.encode("") == "00000000"
    assert heating_times.encode(" 17:00-22:15 ") == "17002215"


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("6:00-8:30", "format"),
        ("06:00", "format"),
        ("25:00-26:00", "format"),
        ("06:00-06:70", "format"),
        ("08:30-06:00", "order"),
        ("06:00-06:00", "order"),
    ],
)
def test_encode_refuses(text, reason):
    with pytest.raises(ValueError, match=reason):
        heating_times.encode(text)
