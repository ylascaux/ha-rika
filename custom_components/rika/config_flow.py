"""Config flow of the RIKA integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import RikaAuthError, RikaClient, RikaError
from .const import CONF_SCHEDULE_ENTITY, DOMAIN

USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCHEDULE_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="schedule")
        )
    }
)


class RikaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the RIKA Firenet account."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RikaOptionsFlow:
        return RikaOptionsFlow()

    async def _async_check(self, email: str, password: str) -> str | None:
        """Try the account; return the error key, or None when it works."""
        client = RikaClient(async_create_clientsession(self.hass), email, password)
        try:
            stoves = await client.list_stoves()
        except RikaAuthError:
            return "invalid_auth"
        except RikaError:
            return "cannot_connect"
        return None if stoves else "no_stoves"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()
            error = await self._async_check(email, user_input[CONF_PASSWORD])
            if error is None:
                return self.async_create_entry(
                    title=email,
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._async_check(
                entry.data[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )


class RikaOptionsFlow(OptionsFlowWithReload):
    """Choose the schedule copied to the stove's heating times."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
