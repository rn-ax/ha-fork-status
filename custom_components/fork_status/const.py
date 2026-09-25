"""Constants for the Fork Status integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "fork_status"

PLATFORMS = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(hours=6)

CONF_ORG = "org"
CONF_GITHUB_TOKEN = "github_token"

GITHUB_API_ROOT = "https://api.github.com"

ATTRIBUTION = "Data provided by the GitHub API"
