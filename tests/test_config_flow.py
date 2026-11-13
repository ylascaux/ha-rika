"""Tests of the config flow."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rika.api import RikaAuthError, RikaConnectionError
from custom_components.rika.const import DOMAIN

INPUT = {CONF_EMAIL: "me@example.com", CONF_PASSWORD: "secret"}


async def test_user_flow(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "me@example.com"
    assert result["data"] == INPUT


async def test_user_flow_errors(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    for error, key in (
        (RikaAuthError, "invalid_auth"),
        (RikaConnectionError, "cannot_connect"),
    ):
        with patch.object(client, "list_stoves", side_effect=error):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], INPUT
            )
        assert result["errors"] == {"base": key}

    with patch.object(client, "list_stoves", return_value={}):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], INPUT
        )
    assert result["errors"] == {"base": "no_stoves"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth(hass, entry, client):
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new"
