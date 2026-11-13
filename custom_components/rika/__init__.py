"""RIKA pellet stoves, through the RIKA Firenet cloud."""

from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import RikaClient
from .coordinator import RikaConfigEntry, RikaCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: RikaConfigEntry) -> bool:
    """Set up the stoves of a RIKA Firenet account."""
    # Its own session: the login lives in a cookie.
    client = RikaClient(
        async_create_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    coordinator = RikaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Version 0.1 had one text entity per heating time range.
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain == Platform.TEXT:
            registry.async_remove(entity.entity_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RikaConfigEntry) -> bool:
    """Unload a RIKA Firenet account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
