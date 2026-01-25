# Clawdbot Integration (Preview)

Run the Clawdbot gateway and messaging connectors directly from the cuti dev container. The addon is enabled by default for testing and can be toggled at any time.

## Enable or disable the addon

```bash
cuti addons list
cuti addons disable clawdbot   # opt-out (no install on future rebuilds)
cuti addons enable clawdbot    # re-enable when you need it again
```

State is stored in `~/.cuti/addons.json`. When enabled, the container image installs the Clawdbot CLI (Node 22 runtime) and mounts persistent directories inside `~/.cuti/clawdbot/`:

- `~/.cuti/clawdbot/config/` → `/home/cuti/.clawdbot` (gateway config, channel creds)
- `~/.cuti/clawdbot/workspaces/<project-id>/` → `/home/cuti/clawd` for that project (workspace, skills, agent files)

`<project-id>` uses the folder name plus a short hash of the absolute path, so two different cuti projects never share the same history/workspace while still avoiding collisions when you open the same project in multiple terminals or containers simultaneously.

Existing setups that used `~/.clawdbot` or `~/clawd` are migrated automatically the next time you run the container.

## Onboarding + gateway

```bash
# 1. Run the wizard (OAuth, Anthropic/OpenAI auth, channel templates)
cuti clawdbot onboard

# 2. Start the gateway and watch logs (auto-selects a port)
cuti clawdbot start

# 3. Inspect or edit clawdbot.json via the container
cuti clawdbot config show

# Optional: pin the port manually if you need a fixed URL
cuti clawdbot gateway --port 18789
```

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

- **Clawdbot CLI missing**: ensure the addon is enabled (`cuti addons list`) and rerun with `--rebuild` (forces the container image to reinstall Clawdbot).
- **Docker/Colima issues**: the wrapper uses the same dependency checks as `cuti container`. Start Docker Desktop or run `colima start` before calling `cuti clawdbot ...`.
- **Channel login prompts not showing**: WhatsApp login requires an interactive terminal. Run the command from a local shell (not from a background job) so the QR renders properly.
- **Ports already in use**: pass `--port` to `cuti clawdbot gateway` to pick a different port, and update the Control UI URL accordingly.

See the upstream documentation for detailed guides:
- Getting started: <https://docs.clawd.bot/start/getting-started>
- WhatsApp: <https://docs.clawd.bot/channels/whatsapp>
- Telegram: <https://docs.clawd.bot/channels/telegram>
- Gateway runbook: <https://docs.clawd.bot/gateway>
