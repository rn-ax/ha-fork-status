# Fork Status

A Home Assistant integration that tracks every fork owned by a GitHub organization or user against its upstream parent.

## What it does

- Auto-discovers every fork under the configured GitHub org/user (no need to list repos manually — add or archive a fork on GitHub and it's picked up on the next scan).
- Exposes one sensor per fork (`sensor.<owner>_<repo>_fork_status`), whose state is how many commits it's behind its upstream parent, with `parent` and `compare_url` attributes.
- Raises a [Repairs](https://www.home-assistant.io/integrations/repairs/) issue for any fork that's behind, clearing it automatically once the fork catches up.
- Never merges anything itself — this is read-only monitoring. Syncing a fork with its upstream is still a manual, reviewed step.

## Configuration

Add the integration via Settings → Devices & Services → Add Integration → Fork Status:

- **GitHub organization or user**: the account whose forks to track (e.g. `rn-ax`).
- **GitHub token**: optional. Without one, only public repos are visible and the unauthenticated GitHub API rate limit (60 requests/hour) applies. A token raises that limit and is required to see private forks.

## Installation

Search for and install `Fork Status` from [HACS](https://hacs.xyz/).
