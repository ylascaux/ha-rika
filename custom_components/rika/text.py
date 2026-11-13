"""Weekly heating times of a RIKA stove, one text per time range."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import heating_times
from .const import DOMAIN, WEEKDAYS
from .coordinator import RikaConfigEntry
from .entity import RikaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RikaHeatingTime(coordinator, stove_id, day, slot)
        for stove_id in coordinator.stoves
        for day in WEEKDAYS
        for slot in (1, 2)
        if f"heatingTime{day}{slot}" in coordinator.data[stove_id]["controls"]
    )


class RikaHeatingTime(RikaEntity, TextEntity):
    """A time range written "06:00-08:30"; empty when the range is not used."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_pattern = heating_times.TEXT_PATTERN
    _attr_native_max = 11

    def __init__(self, coordinator, stove_id: str, day: str, slot: int) -> None:
        super().__init__(coordinator, stove_id, f"heating_time_{day.lower()}_{slot}")
        self._control = f"heatingTime{day}{slot}"

    @property
    def native_value(self) -> str | None:
        return heating_times.decode(self.controls.get(self._control))

    async def async_set_value(self, value: str) -> None:
        try:
            raw = heating_times.encode(value)
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=f"heating_time_{err}",
            ) from err
        await self.async_set_controls(**{self._control: raw})
