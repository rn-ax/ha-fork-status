"""Sensor platform for Fork Status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import ForkStatusDataUpdateCoordinator


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor platform."""
    coordinator: ForkStatusDataUpdateCoordinator = config_entry.runtime_data
    known_repos: set[str] = set()

    def _add_new_entities() -> None:
        new_repos = set(coordinator.data) - known_repos
        if not new_repos:
            return
        known_repos.update(new_repos)
        async_add_entities(
            ForkStatusSensor(coordinator, full_name) for full_name in new_repos
        )

    _add_new_entities()
    config_entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class ForkStatusSensor(CoordinatorEntity, SensorEntity):
    """Reports how many commits a single fork is behind its upstream parent."""

    coordinator: ForkStatusDataUpdateCoordinator

    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:source-fork"
    _attr_native_unit_of_measurement = "commits"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = False

    def __init__(
        self, coordinator: ForkStatusDataUpdateCoordinator, full_name: str
    ) -> None:
        super().__init__(coordinator)
        self._full_name = full_name
        self._attr_unique_id = f"fork_status_{full_name.replace('/', '_')}"
        self._attr_name = f"{full_name} fork status"

    @property
    def available(self) -> bool:
        return super().available and self._full_name in self.coordinator.data

    @property
    def native_value(self) -> int | None:
        fork = self.coordinator.data.get(self._full_name)
        return fork.behind_count if fork else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        fork = self.coordinator.data.get(self._full_name)
        if not fork:
            return {}
        return {
            "parent": fork.parent_full_name,
            "compare_url": fork.compare_url,
        }
