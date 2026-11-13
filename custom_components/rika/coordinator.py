"""Polling of the RIKA cloud."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RikaAuthError, RikaClient, RikaError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type RikaConfigEntry = ConfigEntry[RikaCoordinator]


class RikaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Holds the state of every stove of the account, by stove id."""

    config_entry: RikaConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: RikaConfigEntry, client: RikaClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.stoves: dict[str, str] = {}
        self._send_lock = asyncio.Lock()

    async def _async_setup(self) -> None:
        try:
            self.stoves = await self.client.list_stoves()
        except RikaAuthError as err:
            raise ConfigEntryAuthFailed from err
        except RikaError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return {
                stove_id: await self.client.get_status(stove_id)
                for stove_id in self.stoves
            }
        except RikaAuthError as err:
            raise ConfigEntryAuthFailed from err
        except RikaError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_controls(self, stove_id: str, changes: dict[str, Any]) -> None:
        """Send changed controls to a stove and show them at once."""
        async with self._send_lock:
            try:
                controls = await self.client.set_controls(stove_id, changes)
            except RikaError as err:
                raise HomeAssistantError(
                    f"The RIKA cloud did not take the command: {err}"
                ) from err
            self.async_set_updated_data(
                {**self.data, stove_id: {**self.data[stove_id], "controls": controls}}
            )
