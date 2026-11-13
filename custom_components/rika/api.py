"""Client for the RIKA Firenet cloud (rika-firenet.com)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

import aiohttp

from .const import BASE_URL

TIMEOUT = aiohttp.ClientTimeout(total=20)

_STOVE_LINK = re.compile(r'href="/web/stove/(\d+)"[^>]*>([^<]*)<')


class RikaError(Exception):
    """Base error of the RIKA client."""


class RikaAuthError(RikaError):
    """The cloud refused the credentials."""


class RikaConnectionError(RikaError):
    """The cloud could not be reached or gave an unexpected answer."""


class RikaClient:
    """Talks to rika-firenet.com with the session cookie of the website."""

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._logged_in = False

    async def login(self) -> None:
        """Open a session; a refused login redirects back to the login page."""
        try:
            async with self._session.post(
                f"{BASE_URL}/web/login",
                data={"email": self._email, "password": self._password},
                timeout=TIMEOUT,
            ) as response:
                text = await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RikaConnectionError(f"Login request failed: {err}") from err
        if "/web/logout" not in text:
            self._logged_in = False
            raise RikaAuthError("Login refused")
        self._logged_in = True

    async def _request(self, method: str, path: str, **kwargs: Any) -> str:
        """Send a request, logging in first or again when the session is gone."""
        if not self._logged_in:
            await self.login()
        for attempt in range(2):
            try:
                async with self._session.request(
                    method,
                    f"{BASE_URL}{path}",
                    timeout=TIMEOUT,
                    allow_redirects=False,
                    **kwargs,
                ) as response:
                    status = response.status
                    text = await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise RikaConnectionError(f"{method} {path} failed: {err}") from err
            # An expired session answers 401 on the API and redirects on the pages.
            if status in (301, 302, 401) and attempt == 0:
                await self.login()
                continue
            if status != 200:
                raise RikaConnectionError(f"{method} {path} answered {status}: {text[:100]}")
            return text
        raise RikaConnectionError(f"{method} {path} failed")

    async def list_stoves(self) -> dict[str, str]:
        """Return the stoves of the account, as {stove id: name}."""
        html = await self._request("GET", "/web/summary")
        return {
            stove_id: name.strip() for stove_id, name in _STOVE_LINK.findall(html)
        }

    async def get_status(self, stove_id: str) -> dict[str, Any]:
        """Return the state of a stove: controls, sensors and features."""
        text = await self._request(
            "GET", f"/api/client/{stove_id}/status", params={"nocache": int(time.time())}
        )
        try:
            status = json.loads(text)
        except ValueError as err:
            raise RikaConnectionError(f"Status of {stove_id} is not JSON") from err
        if not isinstance(status, dict) or "controls" not in status:
            raise RikaConnectionError(f"Status of {stove_id} has no controls")
        return status

    async def set_controls(
        self, stove_id: str, changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Change controls of a stove and return the controls sent.

        The cloud takes the whole set of controls with the current revision,
        so they are read again just before sending.
        """
        status = await self.get_status(stove_id)
        controls = {**status["controls"], **changes}
        text = await self._request(
            "POST", f"/api/client/{stove_id}/controls", json=controls
        )
        if "OK" not in text:
            raise RikaConnectionError(f"Controls of {stove_id} refused: {text[:100]}")
        return controls
