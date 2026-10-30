"""Config flow for the MiniMax Usage integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_URL, CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _key_schema(default: str = "") -> vol.Schema:
    return vol.Schema({vol.Required(CONF_API_KEY, default=default): str})


async def _validate_api_key(hass, api_key: str) -> bool:
    """Return True when the key is accepted by the MiniMax usage endpoint."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    base = payload.get("base_resp") or {}
    return base.get("status_code", 0) == 0 and bool(payload.get("model_remains"))


class MiniMaxUsageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MiniMax Usage."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            if await _validate_api_key(self.hass, api_key):
                return self.async_create_entry(
                    title="MiniMax Usage",
                    data={CONF_API_KEY: api_key},
                )
            errors["base"] = "invalid_key"
        return self.async_show_form(
            step_id="user",
            data_schema=_key_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MiniMaxUsageOptionsFlow:
        return MiniMaxUsageOptionsFlow()


class MiniMaxUsageOptionsFlow(OptionsFlow):
    """Allow editing the API key via the UI (gear icon)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }.get(CONF_API_KEY, "")
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            if await _validate_api_key(self.hass, api_key):
                return self.async_create_entry(
                    title="", data={CONF_API_KEY: api_key}
                )
            errors["base"] = "invalid_key"
        return self.async_show_form(
            step_id="init", data_schema=_key_schema(current), errors=errors
        )
