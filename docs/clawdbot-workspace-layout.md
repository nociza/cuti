# Clawdbot Workspace Layout (Cloud vs Sandbox)

## Why this changed

`cuti` now has two runtime profiles:

- `cloud`: full development container behavior (`cuti container`)
- `clawdbot_sandbox`: minimal Clawdbot runtime (`cuti clawdbot ...`)

This doc explains path behavior for both profiles.

## Host storage (source of truth)

Clawdbot state remains on host under:

- `~/.cuti/clawdbot/config/`
- `~/.cuti/clawdbot/workspaces/<project-id>/`

`<project-id>` = workspace folder name + short hash of absolute path, so project histories do not collide.

## Runtime path mapping

| Profile | Host path | Container path | Notes |
|---|---|---|---|
| `cloud` | `~/.cuti/` | `/home/cuti/.cuti-shared` | Broad shared mount used by full dev workflow |
| `cloud` | `~/.cuti/clawdbot/config/` | linked to `/home/cuti/.clawdbot` via bootstrap | Legacy compatibility behavior |
| `cloud` | `~/.cuti/clawdbot/workspaces/<project-id>/` | linked to `/home/cuti/clawd` via bootstrap | Legacy compatibility behavior |
| `clawdbot_sandbox` | `~/.cuti/clawdbot/config/` | `/home/cuti/.clawdbot` | Direct bind mount |
| `clawdbot_sandbox` | `~/.cuti/clawdbot/workspaces/<project-id>/` | `/home/cuti/clawd` | Direct bind mount |
| `clawdbot_sandbox` | current project directory | `/workspace` | Direct bind mount |

## Security difference

In `clawdbot_sandbox`:

- no Docker socket mount
- no host network mode
- no broad host `~/.cuti` mount
- only approved mount targets are allowed
- seccomp profile is enforced (`~/.cuti/seccomp/kuyuchi-clawdbot-seccomp.json` by default)
- startup fails closed if security checklist validation fails

In `cloud`:

- broad developer convenience behavior remains (including shared `.cuti` mount)

## Practical implications

1. Gateway logs still run in foreground unless you explicitly background process management.
2. Backups are still just host-side `~/.cuti/clawdbot/` plus any other required credentials directories.
3. If Clawdbot state appears missing, verify you launched through `cuti clawdbot ...` from the expected workspace so the same `<project-id>` is used.

## Related docs

- Clawdbot usage guide: `docs/clawdbot.md`
- Threat model: `docs/kuyuchi-threat-model.md`
- Runtime audit and split plan: `docs/kuyuchi-container-audit.md`
