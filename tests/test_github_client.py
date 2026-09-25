"""Tests for github_client.py -- no Home Assistant imports needed, plain pytest."""

from __future__ import annotations

import pytest

from custom_components.fork_status.github_client import (
    GitHubAuthError,
    async_fetch_fork_status,
    async_validate_org,
)


class FakeResponse:
    def __init__(self, status: int, payload=None):
        self.status = status
        self._payload = payload

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    async def json(self):
        return self._payload


class FakeSession:
    """Routes GET calls to canned responses keyed by exact URL."""

    def __init__(self, routes: dict[str, FakeResponse]):
        self._routes = routes
        self.calls: list[str] = []

    async def get(self, url, headers=None, params=None):
        self.calls.append(url)
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        if url not in self._routes:
            raise AssertionError(f"Unexpected request: {url}")
        return self._routes[url]


ORG_REPOS_BASE_URL = "https://api.github.com/orgs/rn-ax/repos"
ORG_REPOS_URL = f"{ORG_REPOS_BASE_URL}?per_page=100&page=1"
USER_REPOS_URL = "https://api.github.com/users/rn-ax/repos?per_page=100&page=1"


async def test_validate_org_succeeds_via_org_endpoint():
    session = FakeSession({ORG_REPOS_URL: FakeResponse(200, [])})
    await async_validate_org(session, "rn-ax", None)


async def test_validate_org_falls_back_to_user_endpoint():
    session = FakeSession(
        {
            ORG_REPOS_URL: FakeResponse(404),
            USER_REPOS_URL: FakeResponse(200, [{"fork": False}]),
        }
    )
    await async_validate_org(session, "rn-ax", None)


async def test_validate_org_raises_when_neither_endpoint_matches():
    session = FakeSession(
        {ORG_REPOS_URL: FakeResponse(404), USER_REPOS_URL: FakeResponse(404)}
    )
    with pytest.raises(GitHubAuthError):
        await async_validate_org(session, "rn-ax", None)


async def test_validate_org_raises_on_bad_token_without_trying_user_fallback():
    session = FakeSession({ORG_REPOS_URL: FakeResponse(401)})
    with pytest.raises(GitHubAuthError):
        await async_validate_org(session, "rn-ax", "bad-token")
    assert session.calls == [ORG_REPOS_BASE_URL]


async def test_fetch_fork_status_skips_non_forks_and_builds_compare_url():
    repos_payload = [
        {"full_name": "rn-ax/not-a-fork", "fork": False},
        {"full_name": "rn-ax/healthchecksio", "fork": True},
    ]
    detail = {
        "full_name": "rn-ax/healthchecksio",
        "default_branch": "main",
        "parent": {
            "full_name": "custom-components/healthchecksio",
            "default_branch": "main",
        },
    }
    compare = {"ahead_by": 3}

    session = FakeSession(
        {
            ORG_REPOS_URL: FakeResponse(200, repos_payload),
            "https://api.github.com/repos/rn-ax/healthchecksio": FakeResponse(
                200, detail
            ),
            "https://api.github.com/repos/custom-components/healthchecksio/compare/rn-ax:main...main": FakeResponse(
                200, compare
            ),
        }
    )

    results = await async_fetch_fork_status(session, "rn-ax", None)

    assert len(results) == 1
    fork = results[0]
    assert fork.full_name == "rn-ax/healthchecksio"
    assert fork.parent_full_name == "custom-components/healthchecksio"
    assert fork.behind_count == 3
    assert fork.compare_url == (
        "https://github.com/custom-components/healthchecksio/compare/main...rn-ax:main"
    )


async def test_fetch_fork_status_skips_fork_with_no_parent_info():
    repos_payload = [{"full_name": "rn-ax/weird-fork", "fork": True}]
    detail = {"full_name": "rn-ax/weird-fork", "default_branch": "main"}

    session = FakeSession(
        {
            ORG_REPOS_URL: FakeResponse(200, repos_payload),
            "https://api.github.com/repos/rn-ax/weird-fork": FakeResponse(200, detail),
        }
    )

    results = await async_fetch_fork_status(session, "rn-ax", None)
    assert results == []
