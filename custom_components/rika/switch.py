"""Switches of a RIKA stove."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODE_AUTO, MODE_COMFORT, MODE_MANUAL
from .coordinator import RikaConfigEntry
from .entity import RikaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    for stove_id in coordinator.stoves:
        async_add_entities(
            [
                RikaControlSwitch(coordinator, stove_id, "power", "onOff"),
                RikaControlSwitch(
                    coordinator,
                    stove_id,
                    "frost_protection",
                    "frostProtectionActive",
                    EntityCategory.CONFIG,
                ),
                RikaHeatingTimesSwitch(coordinator, stove_id),
            ]
        )


class RikaControlSwitch(RikaEntity, SwitchEntity):
    """A control that is simply on or off."""

    def __init__(
        self,
        coordinator,
        stove_id: str,
        key: str,
        control: str,
        category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, stove_id, key)
        self._control = control
        self._attr_entity_category = category

    @property
    def is_on(self) -> bool:
        return bool(self.controls.get(self._control))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_controls(**{self._control: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_controls(**{self._control: False})


class RikaHeatingTimesSwitch(RikaEntity, SwitchEntity):
    """Whether the stove follows its weekly heating times.

    With power regulation, following the times is the auto mode and ignoring
    them is the manual mode. Comfort mode has its own flag.
    """

    def __init__(self, coordinator, stove_id: str) -> None:
        super().__init__(coordinator, stove_id, "heating_times")

    @property
    def is_on(self) -> bool:
        mode = self.controls.get("operatingMode")
        if mode == MODE_COMFORT:
            return bool(self.controls.get("heatingTimesActiveForComfort"))
        return mode == MODE_AUTO

    async def _async_set(self, active: bool) -> None:
        if self.controls.get("operatingMode") == MODE_COMFORT:
            await self.async_set_controls(heatingTimesActiveForComfort=active)
        else:
            await self.async_set_controls(
                operatingMode=MODE_AUTO if active else MODE_MANUAL
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)
