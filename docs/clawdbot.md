# Clawdbot Integration (Preview)

Run the Clawdbot gateway and messaging connectors directly from the cuti dev container. The addon is enabled by default and can be toggled at any time. The wrapper handles installing the CLI, wiring persistent storage, and running any command inside the container with the right permissions.

## Enable or disable the addon

```bash
cuti addons list
cuti addons disable clawdbot   # opt-out (no install on future rebuilds)
cuti addons enable clawdbot    # re-enable when you need it again
```

State is stored in `~/.cuti/addons.json`. When enabled, the container image installs the Clawdbot CLI (Node 22 runtime) and mounts persistent directories inside `~/.cuti/clawdbot/`.

## Storage layout & workspace linking

Every time you run `cuti clawdbot …` we relink the expected directories before launching the container:

- `~/.cuti/clawdbot/config/` → `/home/cuti/.clawdbot` (gateway config, channel credentials, channel hooks)
- `~/.cuti/clawdbot/workspaces/<project-id>/` → `/home/cuti/clawd` for that project (agent workspace, logs, skills, session transcripts)

`<project-id>` uses the workspace folder name plus a short hash of its absolute path, so two different cuti projects never collide while the same project opened in multiple shells still shares history. The host still sees the files under `~/.cuti/clawdbot/workspaces/<project-id>/`; inside the container Clawdbot always interacts with `/home/cuti/clawd`.

Legacy installs that used `~/.clawdbot` or `~/clawd` get migrated automatically whenever the wrapper runs.

## Configure the gateway

Use the interactive wizard without leaving the terminal:

```bash
cuti clawdbot config         # full wizard
cuti clawdbot config show    # dump the merged clawdbot.json
```

The command drops into the container with a TTY, so QR screens and prompts render correctly. Because the wrapper runs as root inside the container when needed, edits to `clawdbot.json` and credentials succeed even when the mounted directories are owned by your host user.

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
