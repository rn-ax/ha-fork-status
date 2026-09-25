"""The Fork Status integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_GITHUB_TOKEN, CONF_ORG, PLATFORMS
from .coordinator import ForkStatusDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant import config_entries, core


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
) -> bool:
    """Set up this integration using the UI."""
    config_entry.runtime_data = coordinator = ForkStatusDataUpdateCoordinator(
        hass=hass,
        org=config_entry.data[CONF_ORG],
        github_token=config_entry.data.get(CONF_GITHUB_TOKEN),
        session=async_get_clientsession(hass),
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
