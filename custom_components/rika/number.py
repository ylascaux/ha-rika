"""Numeric settings of a RIKA stove."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RikaConfigEntry
from .entity import RikaEntity, as_float


@dataclass(frozen=True, kw_only=True)
class RikaNumberDescription(NumberEntityDescription):
    control: str
    # The cloud holds temperatures as text and the power as a number.
    as_text: bool = False


NUMBERS = (
    RikaNumberDescription(
        key="heating_power",
        control="heatingPower",
        native_min_value=30,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
    ),
    RikaNumberDescription(
        key="setback_temperature",
        control="setBackTemperature",
        as_text=True,
        native_min_value=12,
        native_max_value=20,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
    ),
    RikaNumberDescription(
        key="frost_protection_temperature",
        control="frostProtectionTemperature",
        as_text=True,
        native_min_value=4,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RikaNumber(coordinator, stove_id, description)
        for stove_id in coordinator.stoves
        for description in NUMBERS
    )


class RikaNumber(RikaEntity, NumberEntity):
    entity_description: RikaNumberDescription

    def __init__(
        self, coordinator, stove_id: str, description: RikaNumberDescription
    ) -> None:
        super().__init__(coordinator, stove_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return as_float(self.controls.get(self.entity_description.control))

    async def async_set_native_value(self, value: float) -> None:
        whole = round(value)
        await self.async_set_controls(
            **{
                self.entity_description.control: str(whole)
                if self.entity_description.as_text
                else whole
            }
        )
