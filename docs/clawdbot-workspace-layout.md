# Clawdbot workspace + symlink layout

## Why the paths look odd
- The cuti container treats `~/.cuti` on the host as the single source of truth for *all* long-lived state (Claude auth, queues, Clawdbot assets). Both the README and the Clawdbot guide call out that every gateway install now persists under `~/.cuti/clawdbot/{config,workspace}` so a rebuild never erases logins or channel setup.
- When `cuti container` (or `cuti clawdbot …`) boots, it bind-mounts the host `~/.cuti` directory to `/home/cuti/.cuti-shared` inside the container, then symlinks `/home/cuti/.cuti` → `/home/cuti/.cuti-shared`. Anything the CLI writes to `~/.cuti` from inside the VM therefore lands back on the host immediately.
- The same bootstrap script also keeps `/home/cuti/.clawdbot` and `/home/cuti/clawd` as *symlinks* that target the persistent `~/.cuti/clawdbot/config` and the per-project workspace folder under `~/.cuti/clawdbot/workspaces/<project-id>`. So the "working directory" you see at `/home/cuti/clawd` is just a view into the host storage. Seeing only the Clawdbot skeleton (AGENTS.md, BOOTSTRAP.md, …) simply means the workspace has been initialized but not yet populated with custom skills.

These behaviors are intentional: they allow every container you launch (or any future Linux VM) to reuse the same WhatsApp login, same OAuth token caches, and the same agent files without copying anything manually.

## Path map: host ↔ container ↔ tools
| Purpose | Host path | Container mount | In-container symlink |
|---------|-----------|-----------------|----------------------|
| Global cuti config & queues | `~/.cuti/` | `/home/cuti/.cuti-shared` | `/home/cuti/.cuti` |
| Clawdbot config (auth, creds) | `~/.cuti/clawdbot/config/` | part of the mount above | `/home/cuti/.clawdbot` |
| Clawdbot workspace for a project | `~/.cuti/clawdbot/workspaces/<name-hash>/` | part of the mount above | `/home/cuti/clawd` |
| Linux-specific Claude creds | `~/.cuti/claude-linux/` | `/home/cuti/.claude-linux` | used via `CLAUDE_CONFIG_DIR` |

The `<name-hash>` component matches the folder basename plus a deterministic short hash of the absolute path, guaranteeing that two different projects never share a Clawdbot workspace even if they have the same name. This mapping is described in `docs/clawdbot.md` and enforced by the container bootstrap script so it works the same way across macOS, Linux, and remote runners.

## Evidence in the repo
- `README.md` (Clawdbot add-on section) states that *all* gateway state now lives under `~/.cuti/clawdbot/` so it can persist across rebuilds.
- `docs/clawdbot.md` reiterates the host→container mapping (`~/.cuti/clawdbot/config` → `/home/cuti/.clawdbot`, `~/.cuti/clawdbot/workspaces/<project-id>` → `/home/cuti/clawd`) and explains why the hashed workspace id exists.
- `docs/claude-account-switching.md` documents the broader container mounts, explicitly calling out that `~/.cuti/` from the host is mounted to `/home/cuti/.cuti-shared` and then symlinked back to `~/.cuti` inside the VM so every helper sees the same path.
- `src/cuti/services/devcontainer.py` contains the bootstrap script that: (1) mounts `~/.cuti` to `/home/cuti/.cuti-shared`, (2) fixes ownership, (3) forces `/home/cuti/.cuti` to be a symlink to that mount, and (4) rewires `/home/cuti/.clawdbot` and `/home/cuti/clawd` to the persistent config/workspace targets for the current project id. The same script is called whether you run `cuti container`, `cuti clawdbot onboard`, or `cuti clawdbot gateway`.

Because the bootstrap owns the symlinks and runs on every container start, the structure you observed is *by design*—if `/home/cuti/clawd` stopped being a symlink you would immediately lose persistence across rebuilds.

## Practical implications
1. **Foreground gateway logs are normal** – the gateway process is supposed to stay attached to your terminal so you can see WhatsApp/websocket events. Backgrounding it is optional (tmux, `nohup`, etc.) but not automatic because the bootstrap script cannot rely on `systemd` inside this environment.
2. **Control UI assets** – the `pnpm ui:build` step happens inside the persistent workspace so the build results survive container restarts. If you see `ERR_PNPM_NO_IMPORTER_MANIFEST_FOUND`, it usually means the bootstrap pointed the build step at the wrong directory rather than a missing workspace.
3. **Backups** – copying or rsyncing `~/.cuti/clawdbot/` and `~/.cuti/claude-linux/` on the host is enough to preserve *all* agent state (channels, OAuth tokens, skill files) because `/home/cuti/clawd` is only a symlink.
4. **Troubleshooting** – if symlinks get corrupted, remove `/home/cuti/.clawdbot` and `/home/cuti/clawd` *inside the container* and rerun `cuti clawdbot gateway`. The bootstrap script will recreate the links pointing at the correct `~/.cuti` targets.

## Further reading
- Clawdbot add-on overview: `README.md`
- Clawdbot integration guide + path details: `docs/clawdbot.md`
- Container mounting strategy: `docs/claude-account-switching.md`
- Bootstrap implementation: `src/cuti/services/devcontainer.py`
- Upstream Clawdbot docs (for channel behavior, gateway architecture, etc.): https://docs.clawd.bot/
