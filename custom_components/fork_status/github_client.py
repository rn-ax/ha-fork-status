"""Minimal async GitHub REST client for the Fork Status integration.

Kept free of any Home Assistant imports so it's plainly unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession

from .const import GITHUB_API_ROOT


class GitHubAuthError(Exception):
    """Raised when the GitHub API rejects the token, or the org/user isn't found."""


@dataclass
class ForkInfo:
    """A single fork's sync status against its parent."""

    full_name: str
    parent_full_name: str
    behind_count: int
    compare_url: str


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _list_owner_repos(
    session: ClientSession, org: str, token: str | None
) -> list[dict[str, Any]]:
    """List every repo for an org or user.

    GitHub uses separate endpoints for organizations and user accounts with
    no single endpoint that works for both, so this tries /orgs/ first and
    falls back to /users/ -- `org` may be either kind of GitHub account.
    """
    headers = _headers(token)
    for kind in ("orgs", "users"):
        repos: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = await session.get(
                f"{GITHUB_API_ROOT}/{kind}/{org}/repos",
                headers=headers,
                params={"per_page": 100, "page": page},
            )
            if resp.status == 404:
                break  # not this kind of account -- try the other one
            if resp.status == 401:
                raise GitHubAuthError("GitHub rejected the provided token")
            resp.raise_for_status()
            batch = await resp.json()
            repos.extend(batch)
            if len(batch) < 100:
                return repos
            page += 1
        if repos:
            return repos
    raise GitHubAuthError(f"'{org}' is not a reachable GitHub organization or user")


async def _repo_detail(
    session: ClientSession, full_name: str, token: str | None
) -> dict[str, Any]:
    resp = await session.get(
        f"{GITHUB_API_ROOT}/repos/{full_name}", headers=_headers(token)
    )
    resp.raise_for_status()
    return await resp.json()


async def _compare_ahead_by(
    session: ClientSession,
    parent_full_name: str,
    fork_owner: str,
    fork_branch: str,
    parent_branch: str,
    token: str | None,
) -> int:
    """Return how many commits the fork is behind its parent's default branch."""
    resp = await session.get(
        f"{GITHUB_API_ROOT}/repos/{parent_full_name}/compare/"
        f"{fork_owner}:{fork_branch}...{parent_branch}",
        headers=_headers(token),
    )
    resp.raise_for_status()
    data = await resp.json()
    return data["ahead_by"]


async def async_validate_org(session: ClientSession, org: str, token: str | None) -> None:
    """Raise GitHubAuthError if `org` isn't a reachable account or the token is bad."""
    await _list_owner_repos(session, org, token)


async def async_fetch_fork_status(
    session: ClientSession, org: str, token: str | None
) -> list[ForkInfo]:
    """Fetch sync status for every fork owned by `org`."""
    repos = await _list_owner_repos(session, org, token)
    results: list[ForkInfo] = []
    for repo in repos:
        if not repo.get("fork"):
            continue
        full_name = repo["full_name"]
        detail = await _repo_detail(session, full_name, token)
        parent = detail.get("parent")
        if not parent:
            continue
        parent_full_name = parent["full_name"]
        fork_owner = full_name.split("/")[0]
        fork_branch = detail["default_branch"]
        parent_branch = parent["default_branch"]
        behind_count = await _compare_ahead_by(
            session, parent_full_name, fork_owner, fork_branch, parent_branch, token
        )
        results.append(
            ForkInfo(
                full_name=full_name,
                parent_full_name=parent_full_name,
                behind_count=behind_count,
                compare_url=(
                    f"https://github.com/{parent_full_name}/compare/"
                    f"{parent_branch}...{fork_owner}:{fork_branch}"
                ),
            )
        )
    return results
