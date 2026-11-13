"""Thermostat of a RIKA stove."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODE_AUTO, MODE_COMFORT, MODE_MANUAL
from .coordinator import RikaConfigEntry
from .entity import RikaEntity, as_float

PRESETS = {"manual": MODE_MANUAL, "auto": MODE_AUTO, "comfort": MODE_COMFORT}

# statusMainState: ignition, start-up, regulation
HEATING_STATES = (2, 3, 4)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RikaClimate(coordinator, stove_id) for stove_id in coordinator.stoves)


class RikaClimate(RikaEntity, ClimateEntity):
    """On/off, operating mode and room set point."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = 1
    _attr_min_temp = 14
    _attr_max_temp = 28
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = list(PRESETS)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, stove_id: str) -> None:
        super().__init__(coordinator, stove_id, "stove")

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT if self.controls.get("onOff") else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if not self.controls.get("onOff"):
            return HVACAction.OFF
        if self.sensors.get("statusMainState") in HEATING_STATES:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        mode = self.controls.get("operatingMode")
        return next((name for name, value in PRESETS.items() if value == mode), None)

    @property
    def current_temperature(self) -> float | None:
        return as_float(self.sensors.get("inputRoomTemperature"))

    @property
    def target_temperature(self) -> float | None:
        # The stove follows the set point in comfort mode only; in manual and
        # auto it runs at the chosen power.
        if self.controls.get("operatingMode") != MODE_COMFORT:
            return None
        return as_float(self.controls.get("targetTemperature"))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.async_set_controls(onOff=hvac_mode == HVACMode.HEAT)

    async def async_turn_on(self) -> None:
        await self.async_set_controls(onOff=True)

    async def async_turn_off(self) -> None:
        await self.async_set_controls(onOff=False)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.async_set_controls(operatingMode=PRESETS[preset_mode])

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the room set point, which switches the stove to comfort mode."""
        await self.async_set_controls(
            targetTemperature=str(round(kwargs[ATTR_TEMPERATURE])),
            operatingMode=MODE_COMFORT,
        )
