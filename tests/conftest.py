"""Fixtures for the RIKA tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.rika.const import DOMAIN

STOVE_ID = "12345678"
STATUS = json.loads((Path(__file__).parent / "fixtures" / "status.json").read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration under test."""


class FakeClient:
    """Stands for the cloud: holds one stove and takes its commands."""

    def __init__(self, *args) -> None:
        self.status = copy.deepcopy(STATUS)
        self.sent: list[dict] = []

    async def list_stoves(self) -> dict[str, str]:
        return {STOVE_ID: "Salon"}

    async def get_status(self, stove_id: str) -> dict:
        return copy.deepcopy(self.status)

    async def set_controls(self, stove_id: str, changes: dict) -> dict:
        self.sent.append(changes)
        self.status["controls"].update(changes)
        return copy.deepcopy(self.status["controls"])


@pytest.fixture
def client():
    fake = FakeClient()
    with (
        patch("custom_components.rika.RikaClient", return_value=fake),
        patch("custom_components.rika.config_flow.RikaClient", return_value=fake),
    ):
        yield fake


@pytest.fixture
async def entry(hass, client):
    """The integration set up with the fake stove."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="me@example.com",
        data={CONF_EMAIL: "me@example.com", CONF_PASSWORD: "secret"},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
