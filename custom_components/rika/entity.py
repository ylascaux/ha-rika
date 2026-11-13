"""Base entity of the RIKA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BASE_URL, DOMAIN
from .coordinator import RikaCoordinator


class RikaEntity(CoordinatorEntity[RikaCoordinator]):
    """An entity of one stove."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RikaCoordinator, stove_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._stove_id = stove_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{stove_id}_{key}"
        version = self.sensors.get("parameterVersionMainBoard")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, stove_id)},
            name=coordinator.stoves[stove_id],
            manufacturer="RIKA",
            model=self.status.get("stoveType"),
            sw_version=f"{version / 100:.2f}" if isinstance(version, int) else None,
            configuration_url=f"{BASE_URL}/web/stove/{stove_id}",
        )

    @property
    def status(self) -> dict[str, Any]:
        return self.coordinator.data[self._stove_id]

    @property
    def controls(self) -> dict[str, Any]:
        return self.status.get("controls", {})

    @property
    def sensors(self) -> dict[str, Any]:
        return self.status.get("sensors", {})

    async def async_set_controls(self, **changes: Any) -> None:
        await self.coordinator.async_set_controls(self._stove_id, changes)


def as_float(value: Any) -> float | None:
    """Read a number the cloud may give as text."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
