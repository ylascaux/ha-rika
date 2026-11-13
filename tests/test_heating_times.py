"""Tests of the heating times copied from a Home Assistant schedule."""

from datetime import time

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.rika import heating_times
from custom_components.rika.const import CONF_SCHEDULE_ENTITY, DOMAIN

SCHEDULE = "schedule.chauffage"


@pytest.fixture
def expected_lingering_timers() -> bool:
    """The schedule helper keeps a timer for its next change."""
    return True


def test_from_schedule():
    controls = heating_times.from_schedule(
        {
            "monday": [
                # Given out of order, and once as text.
                {"from": time(17, 0), "to": time(22, 15)},
                {"from": "06:00:00", "to": "08:30:00"},
            ],
            "tuesday": [{"from": time(7, 30), "to": time.max}],
            "wednesday": [],
        }
    )
    assert len(controls) == 14
    assert controls["heatingTimeMon1"] == "06000830"
    assert controls["heatingTimeMon2"] == "17002215"
    # Home Assistant gives the end of the day as the last instant of it.
    assert controls["heatingTimeTue1"] == "07302359"
    assert controls["heatingTimeTue2"] == "00000000"
    assert controls["heatingTimeWed1"] == "00000000"
    assert controls["heatingTimeSun2"] == "00000000"


def test_from_schedule_too_many_ranges():
    blocks = [{"from": time(h, 0), "to": time(h + 1, 0)} for h in (6, 12, 18)]
    with pytest.raises(heating_times.TooManyRanges, match="friday"):
        heating_times.from_schedule({"friday": blocks})


async def setup_schedule(hass, **days) -> None:
    assert await async_setup_component(
        hass, "schedule", {"schedule": {"chauffage": {"name": "Chauffage", **days}}}
    )


async def setup_entry(hass, options=None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="me@example.com",
        data={CONF_EMAIL: "me@example.com", CONF_PASSWORD: "secret"},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_schedule_is_copied(hass, client):
    await setup_schedule(
        hass,
        monday=[
            {"from": "06:00:00", "to": "08:30:00"},
            {"from": "17:00:00", "to": "22:00:00"},
        ],
        saturday=[{"from": "08:00:00", "to": "23:00:00"}],
    )
    entry = await setup_entry(hass, {CONF_SCHEDULE_ENTITY: SCHEDULE})

    # Only the ranges that differ from the stove's are sent.
    assert client.sent == [
        {
            "heatingTimeMon1": "06000830",
            "heatingTimeMon2": "17002200",
            "heatingTimeSat1": "08002300",
        }
    ]

    # Nothing more to send while the schedule stays the same.
    await entry.runtime_data.async_refresh()
    assert len(client.sent) == 1

    # A range changed on the stove is put back.
    client.status["controls"]["heatingTimeMon1"] = "05000600"
    await entry.runtime_data.async_refresh()
    assert client.sent[-1] == {"heatingTimeMon1": "06000830"}


async def test_no_schedule_chosen(hass, client):
    await setup_schedule(hass, monday=[{"from": "06:00:00", "to": "08:30:00"}])
    await setup_entry(hass)
    assert client.sent == []


async def test_too_many_ranges(hass, client):
    await setup_schedule(
        hass,
        monday=[
            {"from": "06:00:00", "to": "07:00:00"},
            {"from": "12:00:00", "to": "13:00:00"},
            {"from": "18:00:00", "to": "19:00:00"},
        ],
    )
    await setup_entry(hass, {CONF_SCHEDULE_ENTITY: SCHEDULE})

    assert client.sent == []
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "schedule_too_many_ranges")
    assert issue is not None
    assert issue.translation_placeholders == {"schedule": SCHEDULE}


async def test_options_flow(hass, entry, client):
    await setup_schedule(hass, sunday=[{"from": "09:00:00", "to": "21:00:00"}])

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCHEDULE_ENTITY: SCHEDULE}
    )
    await hass.async_block_till_done()

    # The entry is reloaded with the schedule, which is copied at once.
    assert entry.options == {CONF_SCHEDULE_ENTITY: SCHEDULE}
    assert client.sent == [{"heatingTimeSun1": "09002100"}]


async def test_old_text_entities_are_removed(hass, client):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="me@example.com",
        data={CONF_EMAIL: "me@example.com", CONF_PASSWORD: "secret"},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "text", DOMAIN, "12345678_heating_time_mon_1", config_entry=entry
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(old.entity_id) is None
