"""Coordinator for the Fork Status integration."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .github_client import ForkInfo, GitHubAuthError, async_fetch_fork_status

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = getLogger(__name__)


def _issue_id(full_name: str) -> str:
    return f"fork_behind_{full_name.replace('/', '_')}"


class ForkStatusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, ForkInfo]]):
    """Fetches every fork's sync status and keeps Repairs issues in sync with it."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        org: str,
        github_token: str | None,
        session: ClientSession,
    ) -> None:
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self._org = org
        self._github_token = github_token
        self._session = session
        self._known_issue_ids: set[str] = set()

    async def _async_update_data(self) -> dict[str, ForkInfo]:
        try:
            forks = await async_fetch_fork_status(
                self._session, self._org, self._github_token
            )
        except GitHubAuthError as error:
            raise UpdateFailed(str(error)) from error
        except Exception as error:
            raise UpdateFailed(error) from error

        data = {fork.full_name: fork for fork in forks}
        self._sync_repairs(data)
        return data

    def _sync_repairs(self, data: dict[str, ForkInfo]) -> None:
        current_issue_ids: set[str] = set()
        for fork in data.values():
            if fork.behind_count <= 0:
                continue
            issue_id = _issue_id(fork.full_name)
            current_issue_ids.add(issue_id)
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="fork_behind",
                translation_placeholders={
                    "repo": fork.full_name,
                    "parent": fork.parent_full_name,
                    "behind_count": str(fork.behind_count),
                },
                learn_more_url=fork.compare_url,
            )

        for stale_issue_id in self._known_issue_ids - current_issue_ids:
            ir.async_delete_issue(self.hass, DOMAIN, stale_issue_id)

        self._known_issue_ids = current_issue_ids
