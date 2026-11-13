"""Polling of the RIKA cloud."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import heating_times
from .api import RikaAuthError, RikaClient, RikaError
from .const import CONF_SCHEDULE_ENTITY, DOMAIN, SCAN_INTERVAL

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
            data = {
                stove_id: await self.client.get_status(stove_id)
                for stove_id in self.stoves
            }
        except RikaAuthError as err:
            raise ConfigEntryAuthFailed from err
        except RikaError as err:
            raise UpdateFailed(str(err)) from err
        await self._async_copy_schedule(data)
        return data

    async def _async_read_schedule(self) -> dict[str, str] | None:
        """Return the heating times the chosen schedule asks for, if any."""
        entity_id = self.config_entry.options.get(CONF_SCHEDULE_ENTITY)
        if (
            not entity_id
            or self.hass.states.get(entity_id) is None
            or not self.hass.services.has_service("schedule", "get_schedule")
        ):
            return None
        try:
            response = await self.hass.services.async_call(
                "schedule",
                "get_schedule",
                {"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
            times = heating_times.from_schedule(response[entity_id])
        except heating_times.TooManyRanges:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "schedule_too_many_ranges",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="schedule_too_many_ranges",
                translation_placeholders={"schedule": entity_id},
            )
            return None
        except (HomeAssistantError, KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Schedule %s could not be read: %s", entity_id, err)
            return None
        ir.async_delete_issue(self.hass, DOMAIN, "schedule_too_many_ranges")
        return times

    async def _async_copy_schedule(self, data: dict[str, dict[str, Any]]) -> None:
        """Send the heating times that differ from the chosen schedule."""
        times = await self._async_read_schedule()
        if times is None:
            return
        for stove_id, status in data.items():
            controls = status["controls"]
            changes = {
                name: value
                for name, value in times.items()
                if name in controls and controls[name] != value
            }
            if not changes:
                continue
            try:
                async with self._send_lock:
                    status["controls"] = await self.client.set_controls(
                        stove_id, changes
                    )
            except RikaError as err:
                # Tried again at the next update.
                _LOGGER.warning("Heating times of %s not sent: %s", stove_id, err)

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
