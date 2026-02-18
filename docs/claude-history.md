# Claude Code History & Resume Guide

Claude Code stores every coding/chat session as JSONL logs under the project-specific `projects/` directory inside your Claude config folder.

| Environment | Default log root |
|-------------|------------------|
| macOS host | `~/.claude/projects/` |
| cuti container | `~/.cuti/claude-linux/projects/` (mounted via `CLAUDE_CONFIG_DIR`) |

Each subdirectory name is a sanitized version of the workspace path (for example, `/workspace` → `-workspace`, `/Volumes/…/cuti` → `-Volumes-…-cuti`). Inside you’ll find one `<session-id>.jsonl` per conversation with every user/assistant exchange.

## CLI quick reference

The new `cuti history` commands surface those logs without digging through the filesystem:

```bash
# Show the ten most recent sessions in the current repo
cuti history list

# Display the last 40 messages from the latest session
cuti history show latest --limit 40

# Resume an older session (full UUID or the index from `list`)
cuti history resume 3

# Inspect logs for a different path or aggregate all workspaces
cuti history list --workspace /Volumes/Projects/app --all
```

`resume` invokes the official `claude --resume <session-id>` command, so you keep the IDE integrations, tools, and channel permissions configured in your environment. The command defaults to the most recent session when no identifier is supplied.

## How it works

1. The history service looks for Claude’s `projects/` directories under `CLAUDE_CONFIG_DIR`, `~/.cuti/claude-linux/`, and `~/.claude/`.
2. Log files are filtered by workspace slug (matching the directory you run the command from) so you only see relevant sessions.
3. `show` flattens the JSONL transcript into simple USER/ASSISTANT blocks for easy review; `resume` shells out to `claude --resume` and picks up right where the transcript ended.

> **Tip:** Logs live entirely inside your user-owned `~/.claude` / `~/.cuti/claude-linux` directories, so standard backups of those folders preserve every coding session from both host and container runs.

