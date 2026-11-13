"""Sensors of a RIKA stove."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RikaConfigEntry
from .entity import RikaEntity, as_float

STATES = [
    "off",
    "standby",
    "external_request",
    "ignition",
    "starting_up",
    "running",
    "cleaning",
    "big_cleaning",
    "burn_off",
    "frost_protection",
    "lid_open",
    "empty_tank",
    "not_ignited",
    "error",
]

# statusMainState, for the states that do not depend on statusSubState
MAIN_STATES = {2: "ignition", 3: "starting_up", 4: "running", 6: "burn_off"}


def stove_state(status: dict[str, Any]) -> str | None:
    """Name what the stove is doing, problems first."""
    sensors = status.get("sensors", {})
    error = sensors.get("statusError")
    sub_error = sensors.get("statusSubError")
    main = sensors.get("statusMainState")
    sub = sensors.get("statusSubState")
    if sensors.get("statusWarning") == 2:
        return "lid_open"
    if error == 1 and sub_error == 2:
        return "empty_tank"
    if error == 8 and sub_error == 16:
        return "not_ignited"
    if error:
        return "error"
    if sensors.get("statusFrostStarted"):
        return "frost_protection"
    if main == 1:
        if sub == 0:
            return "off"
        return "external_request" if sub == 2 else "standby"
    if main == 5:
        return "big_cleaning" if sub in (3, 4) else "cleaning"
    return MAIN_STATES.get(main)


@dataclass(frozen=True, kw_only=True)
class RikaSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]


def _sensor(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda status: status.get("sensors", {}).get(name)


def _number(name: str) -> Callable[[dict[str, Any]], float | None]:
    return lambda status: as_float(status.get("sensors", {}).get(name))


SENSORS = (
    RikaSensorDescription(
        key="state",
        device_class=SensorDeviceClass.ENUM,
        options=STATES,
        value=stove_state,
    ),
    RikaSensorDescription(
        key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value=_number("inputRoomTemperature"),
    ),
    RikaSensorDescription(
        key="flame_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value=_number("inputFlameTemperature"),
    ),
    RikaSensorDescription(
        key="pellets_consumed",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        value=_sensor("parameterFeedRateTotal"),
    ),
    RikaSensorDescription(
        key="pellets_before_service",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        value=_sensor("parameterServiceCountdownKg"),
    ),
    RikaSensorDescription(
        key="runtime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value=_sensor("parameterRuntimePellets"),
    ),
    RikaSensorDescription(
        key="ignition_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_sensor("parameterIgnitionCount"),
    ),
    RikaSensorDescription(
        key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_sensor("statusError"),
    ),
    RikaSensorDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_sensor("statusWifiStrength"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RikaSensor(coordinator, stove_id, description)
        for stove_id in coordinator.stoves
        for description in SENSORS
    )


class RikaSensor(RikaEntity, SensorEntity):
    entity_description: RikaSensorDescription

    def __init__(
        self, coordinator, stove_id: str, description: RikaSensorDescription
    ) -> None:
        super().__init__(coordinator, stove_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.status)
