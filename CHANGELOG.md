# Changelog

All notable changes to cuti are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed (breaking)

cuti is now focused on its headline value — the instant, containerized Claude Code
dev environment — and the surrounding provider/account/history/usage tooling. Several
obsolete or unused subsystems were removed (no backward compatibility is provided):

- **Multi-agent orchestration**: the in-process `cuti.agents` package (pool/router/
  Gemini agents), the `cuti agent` command, and the orphaned service-layer
  orchestration modules.
- **Prompt/command queue**: `core/queue.py`, `core/storage.py`, `queue_service`, the
  `cuti queue` command group, and the top-level `cuti start` / `add` / `status`
  aliases. The web ops console no longer surfaces queue state.
- **Custom todo & alias subsystems** (`cuti todo`, `cuti alias`): these duplicated
  Claude Code's native todo tracking and primarily existed to feed the removed queue.
- **Large amounts of dead code** with no importers: duplicate usage monitors,
  unused Claude stream/SDK interfaces, abandoned workspace/log-sync/task-history
  services, backward-compat shims, and an orphaned `container_status` command.
- The unused, mislabeled `docker/seccomp` profile (it was never wired into container
  launch).

### Security

- The host **Docker socket is no longer mounted by default** for `cuti container`.
  Opt in with `--docker-socket` only when you need Docker-in-Docker; the socket is
  root-equivalent on the host.
- Saved (inactive) Claude account credentials are now **shadowed inside the
  container**, so an agent can only see the active account's tokens.
- The container's Docker socket permission was tightened from world-writable (`666`)
  to group-only (`660`).
- Account names are sanitized and **path-traversal-checked** before any filesystem
  operation (including `delete`'s `rmtree`); credential directories are created
  `0700` and secret files are written atomically as `0600`.
- `cuti claude add-api-key` now prompts for the secret with hidden input by default,
  keeping it out of shell history and process listings.
- The ops console's CORS policy no longer combines a wildcard origin with credentials.

### Changed

- A clear single value proposition across the README, package metadata, and CLI help.
- `cuti --help` now shows commands grouped by area with `container` as the primary
  "Getting started" command; bare `cuti` shows help instead of an error.
- Environment variables renamed from `CLAUDE_QUEUE_*` to `CUTI_*`.
- The package version is single-sourced from package metadata (the web app no longer
  reports a hardcoded version).
- `run.py` is now a thin developer bootstrap shim; use the `cuti` / `cuti-web`
  console scripts.

### Added

- GitHub Actions CI (lint, format check, type check, tests across Python 3.10–3.12,
  and a build job) and a tag-driven PyPI release workflow.
- A `.pre-commit-config.yaml` wiring ruff and black.
- Lazy, side-effect-free host-tool probing in `DevContainerService`, making it
  unit-testable without shelling out at construction time.
