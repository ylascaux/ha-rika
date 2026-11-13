"""Tests of the entities, on the state of a real SUMO."""

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.rika.sensor import stove_state

from .conftest import STATUS, STOVE_ID


def entity_id(hass, platform: str, key: str) -> str:
    found = er.async_get(hass).async_get_entity_id(platform, "rika", f"{STOVE_ID}_{key}")
    assert found, f"no {platform} entity for {key}"
    return found


async def call(hass, domain: str, service: str, target: str, **data) -> None:
    await hass.services.async_call(
        domain, service, {"entity_id": target, **data}, blocking=True
    )


async def test_states(hass, entry):
    climate = hass.states.get(entity_id(hass, "climate", "stove"))
    assert climate.state == "heat"
    assert climate.attributes["hvac_action"] == "idle"
    assert climate.attributes["preset_mode"] == "comfort"
    assert climate.attributes["temperature"] == 16
    assert climate.attributes["current_temperature"] == 18.5
    assert climate.attributes["min_temp"] == 14
    assert climate.attributes["max_temp"] == 28

    assert hass.states.get(entity_id(hass, "switch", "power")).state == "on"
    assert hass.states.get(entity_id(hass, "switch", "heating_times")).state == "on"
    assert hass.states.get(entity_id(hass, "switch", "frost_protection")).state == "off"
    assert hass.states.get(entity_id(hass, "number", "heating_power")).state == "100.0"
    assert hass.states.get(entity_id(hass, "number", "setback_temperature")).state == "14.0"
    assert hass.states.get(entity_id(hass, "sensor", "state")).state == "standby"
    assert hass.states.get(entity_id(hass, "sensor", "room_temperature")).state == "18.5"
    assert hass.states.get(entity_id(hass, "sensor", "pellets_consumed")).state == "2131"
    assert hass.states.get(entity_id(hass, "binary_sensor", "problem")).state == "off"
    assert hass.states.get(entity_id(hass, "binary_sensor", "door")).state == "off"
    assert hass.states.get(entity_id(hass, "binary_sensor", "connection")).state == "on"


async def test_power(hass, entry, client):
    switch = entity_id(hass, "switch", "power")
    climate = entity_id(hass, "climate", "stove")

    await call(hass, "switch", "turn_off", switch)
    assert client.sent[-1] == {"onOff": False}
    assert hass.states.get(switch).state == "off"
    assert hass.states.get(climate).state == "off"
    assert hass.states.get(climate).attributes["hvac_action"] == "off"

    await call(hass, "climate", "turn_on", climate)
    assert client.sent[-1] == {"onOff": True}
    assert hass.states.get(switch).state == "on"

    await call(hass, "climate", "set_hvac_mode", climate, hvac_mode="off")
    assert client.sent[-1] == {"onOff": False}


async def test_temperature_and_modes(hass, entry, client):
    climate = entity_id(hass, "climate", "stove")

    await call(hass, "climate", "set_preset_mode", climate, preset_mode="manual")
    assert client.sent[-1] == {"operatingMode": 0}
    # Power regulation: no room set point.
    assert hass.states.get(climate).attributes["temperature"] is None

    # Setting a room temperature brings the stove back to comfort mode.
    await call(hass, "climate", "set_temperature", climate, temperature=22)
    assert client.sent[-1] == {"targetTemperature": "22", "operatingMode": 2}
    assert hass.states.get(climate).attributes["temperature"] == 22
    assert hass.states.get(climate).attributes["preset_mode"] == "comfort"


async def test_heating_times_switch(hass, entry, client):
    switch = entity_id(hass, "switch", "heating_times")
    climate = entity_id(hass, "climate", "stove")

    # Comfort mode has its own flag.
    await call(hass, "switch", "turn_off", switch)
    assert client.sent[-1] == {"heatingTimesActiveForComfort": False}

    # With power regulation, the times make the difference between manual and auto.
    await call(hass, "climate", "set_preset_mode", climate, preset_mode="manual")
    assert hass.states.get(switch).state == "off"
    await call(hass, "switch", "turn_on", switch)
    assert client.sent[-1] == {"operatingMode": 1}
    assert hass.states.get(climate).attributes["preset_mode"] == "auto"
    await call(hass, "switch", "turn_off", switch)
    assert client.sent[-1] == {"operatingMode": 0}


async def test_numbers(hass, entry, client):
    await call(
        hass, "number", "set_value", entity_id(hass, "number", "heating_power"), value=70
    )
    assert client.sent[-1] == {"heatingPower": 70}

    await call(
        hass,
        "number",
        "set_value",
        entity_id(hass, "number", "frost_protection_temperature"),
        value=6,
    )
    assert client.sent[-1] == {"frostProtectionTemperature": "6"}

    await call(hass, "switch", "turn_on", entity_id(hass, "switch", "frost_protection"))
    assert client.sent[-1] == {"frostProtectionActive": True}


@pytest.mark.parametrize(
    ("sensors", "expected"),
    [
        ({"statusMainState": 1, "statusSubState": 0}, "off"),
        ({"statusMainState": 1, "statusSubState": 2}, "external_request"),
        ({"statusMainState": 2}, "ignition"),
        ({"statusMainState": 4}, "running"),
        ({"statusMainState": 5, "statusSubState": 1}, "cleaning"),
        ({"statusMainState": 5, "statusSubState": 3}, "big_cleaning"),
        ({"statusMainState": 6}, "burn_off"),
        ({"statusMainState": 4, "statusError": 1, "statusSubError": 2}, "empty_tank"),
        ({"statusMainState": 4, "statusError": 8, "statusSubError": 16}, "not_ignited"),
        ({"statusMainState": 4, "statusError": 32768}, "error"),
        ({"statusMainState": 4, "statusWarning": 2}, "lid_open"),
        ({"statusMainState": 1, "statusSubState": 1, "statusFrostStarted": True}, "frost_protection"),
        ({"statusMainState": 99}, None),
    ],
)
def test_stove_state(sensors, expected):
    assert stove_state({"sensors": {**STATUS["sensors"], **sensors}}) == expected
