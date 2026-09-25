"""Config flow for the Fork Status integration."""

from __future__ import annotations

from logging import getLogger
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_GITHUB_TOKEN, CONF_ORG, DOMAIN
from .github_client import GitHubAuthError, async_validate_org

LOGGER = getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ORG): str,
        vol.Optional(CONF_GITHUB_TOKEN): str,
    }
)


class ForkStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fork Status."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ORG].lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                await async_validate_org(
                    session, user_input[CONF_ORG], user_input.get(CONF_GITHUB_TOKEN)
                )
            except GitHubAuthError:
                errors["base"] = "auth"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_ORG], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
