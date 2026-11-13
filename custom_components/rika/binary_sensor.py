"""Binary sensors of a RIKA stove."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import OFFLINE_AFTER_MINUTES
from .coordinator import RikaConfigEntry
from .entity import RikaEntity


@dataclass(frozen=True, kw_only=True)
class RikaBinarySensorDescription(BinarySensorEntityDescription):
    is_on: Callable[[dict[str, Any]], bool | None]


def _open(name: str) -> Callable[[dict[str, Any]], bool | None]:
    """The stove reports its contacts as true when closed."""

    def is_open(status: dict[str, Any]) -> bool | None:
        closed = status.get("sensors", {}).get(name)
        return None if closed is None else not closed

    return is_open


BINARY_SENSORS = (
    RikaBinarySensorDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on=lambda status: bool(status.get("sensors", {}).get("statusError")),
    ),
    RikaBinarySensorDescription(
        key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        is_on=_open("inputDoor"),
    ),
    RikaBinarySensorDescription(
        key="pellet_lid",
        device_class=BinarySensorDeviceClass.OPENING,
        is_on=_open("inputCover"),
    ),
    RikaBinarySensorDescription(
        key="connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on=lambda status: status.get("lastSeenMinutes", 0) <= OFFLINE_AFTER_MINUTES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RikaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        RikaBinarySensor(coordinator, stove_id, description)
        for stove_id in coordinator.stoves
        for description in BINARY_SENSORS
    )


class RikaBinarySensor(RikaEntity, BinarySensorEntity):
    entity_description: RikaBinarySensorDescription

    def __init__(
        self, coordinator, stove_id: str, description: RikaBinarySensorDescription
    ) -> None:
        super().__init__(coordinator, stove_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on(self.status)
