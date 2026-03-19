# Clawdbot Sandbox

Run the legacy Clawdbot gateway and messaging connectors through cuti's separate `clawdbot_sandbox` runtime profile.

This is not part of the agent provider system. If you want the OpenClaw provider inside the standard cloud dev container, use `cuti providers enable openclaw` instead. This document covers the older `cuti clawdbot ...` workflow, which keeps its own storage under `~/.cuti/clawdbot/` and applies a stricter sandbox profile.

The sandbox installs the Clawdbot CLI on demand if it is missing, so there is no addon flag or separate enable/disable state anymore.

## Storage layout

Every time you run `cuti clawdbot …`, the sandbox profile bind-mounts these host paths directly:

- `~/.cuti/clawdbot/config/` → `/home/cuti/.clawdbot` (gateway config, channel credentials, channel hooks)
- `~/.cuti/clawdbot/workspaces/<project-id>/` → `/home/cuti/clawd` for that project (agent workspace, logs, skills, session transcripts)

`<project-id>` uses the workspace folder name plus a short hash of its absolute path, so two different cuti projects never collide while the same project opened in multiple shells still shares history. The host still sees files under `~/.cuti/clawdbot/workspaces/<project-id>/`; inside the container Clawdbot interacts with `/home/cuti/clawd`.

Legacy installs that used `~/.clawdbot` or `~/clawd` are migrated into `~/.cuti/clawdbot/...` automatically.

## Security notes

- Clawdbot sessions run in `clawdbot_sandbox`: Docker socket is never mounted, and start fails closed if policy checks fail.
- The sandbox profile does not use host networking; gateway ports are explicitly published (`127.0.0.1:<port>:<port>`).
- Only the workspace, Clawdbot config, and Clawdbot workspace mounts are allowed in sandbox mode.
- A seccomp profile is enforced in sandbox mode (`docker/seccomp/kuyuchi-clawdbot-seccomp.json`, copied to `~/.cuti/seccomp/` at runtime).
- Control UI assets are built only from the globally installed Clawdbot package directory; workspace dependencies can’t inject build steps by shadowing `node_modules/clawdbot`.
- Channel credentials live under `~/.cuti/clawdbot/`; keep that directory in your user account only and avoid sharing it with other host users.

## Configure the gateway

Use the interactive wizard without leaving the terminal:

```bash
cuti clawdbot config         # full wizard
cuti clawdbot config show    # dump the merged clawdbot.json
```

The command drops into the container with a TTY, so QR screens and prompts render correctly. Config edits are persisted through the mounted `~/.cuti/clawdbot/config` directory.

## Onboarding + gateway

```bash
# 1. Recommended: one command bring-up (auto-configure when needed)
cuti clawdbot up

# 2. Manual wizard (if you want explicit setup first)
cuti clawdbot onboard

# 3. Start the gateway and watch logs (auto-selects a port)
cuti clawdbot start

# 4. Inspect or edit clawdbot.json via the container
cuti clawdbot config show

# Optional: pin the port manually if you need a fixed URL
cuti clawdbot gateway --port 18789
```

`cuti clawdbot up` behavior:

1. Checks whether Clawdbot appears configured (config + credentials heuristic).
2. If not configured, opens interactive `clawdbot config`.
3. Starts gateway in the sandbox runtime profile.

`cuti clawdbot start` picks a host port using this order: `--port` flag → `CUTI_CLAWDBOT_PORT` env var → your last saved setting in `~/.cuti/clawdbot/config/clawdbot.json` → the first available port starting at 18789. The CLI prints the chosen Control UI URL (e.g. `http://127.0.0.1:18789`). Pressing `Ctrl+C` now triggers a graceful shutdown sequence so the gateway has time to flush logs, disconnect channels, and the host port is released cleanly.

When you need a predictable port (reverse proxies, bookmarks, etc.) stick with `cuti clawdbot gateway --port <number>`.

## Connect messaging channels

### WhatsApp QR login

```bash
cuti clawdbot channels-login --channel whatsapp
```

Follow the CLI instructions to scan the QR from WhatsApp → Settings → Linked Devices. Credentials are saved under `~/.cuti/clawdbot/config/credentials/whatsapp/<accountId>` on the host so you only need to link once.

### Telegram / Discord / others

Add bot tokens to `~/.cuti/clawdbot/config/clawdbot.json` (per [official docs](https://docs.clawd.bot/channels)) or use the Clawdbot CLI directly:

```bash
cuti clawdbot run channels add --channel telegram --token "123456:ABCDEF"
```

After updating config, restart the gateway (`cuti clawdbot gateway ...`).

## Smoke-test messaging

Use the built-in wrapper to send a test DM through the active gateway:

```bash
cuti clawdbot send --to +15551234567 --message "Hello from cuti + Clawdbot"
```

For more complex workflows, drop into the full CLI:

```bash
cuti clawdbot run status
cuti clawdbot run message send --target +15551234567 --message "Manual command"
```

## Troubleshooting

- **Clawdbot CLI missing**: rerun the command once in an interactive shell; the sandbox now self-installs the legacy CLI when needed. If the container image itself is stale, retry with `cuti clawdbot start --rebuild`.
- **Docker/Colima issues**: the wrapper uses the same dependency checks as `cuti container`. Start Docker Desktop or run `colima start` before calling `cuti clawdbot ...`.
- **Channel login prompts not showing**: WhatsApp login requires an interactive terminal. Run the command from a local shell (not from a background job) so the QR renders properly.
- **Ports already in use**: pass `--port` to `cuti clawdbot gateway` to pick a different port, and update the Control UI URL accordingly.
- **Security policy start failure**: if startup reports a policy violation, check `cuti` version and avoid overriding container runtime flags manually.
- **Custom seccomp profile**: set `CUTI_CLAWDBOT_SECCOMP_PROFILE=/absolute/path/to/profile.json` to override the default profile.

See the upstream documentation for detailed guides:
- Getting started: <https://docs.clawd.bot/start/getting-started>
- WhatsApp: <https://docs.clawd.bot/channels/whatsapp>
- Telegram: <https://docs.clawd.bot/channels/telegram>
- Gateway runbook: <https://docs.clawd.bot/gateway>
