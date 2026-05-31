# Project goals

## What cuti is

cuti is the fastest way to get a **clean, isolated Claude Code dev environment**:
`cuti container` launches a reproducible Docker workspace with Claude Code (or another
agent-CLI provider) ready to go, plus the operational tooling around it — provider
management, Claude account switching, session history, and usage analytics.

cuti is **additive to Claude Code**. It does not re-implement Claude Code's own
capabilities (todos, subagents, session resume, hooks, slash commands). Where those
exist natively, cuti integrates with them rather than duplicating them.

## Principles

- **Container-first.** The headline experience is one command to a working,
  disposable Claude Code environment. Everything else supports that.
- **Secure by default.** No host-root escape hatches or broad credential exposure
  unless the user explicitly opts in.
- **Thin and legible.** Prefer integrating with provider CLIs over re-building their
  features. Keep the surface small enough that a new contributor can read it.

## Roadmap

- **Containers**: faster cold start, more host runtimes, clearer rebuild story.
- **Providers**: smoother auth/setup for Claude, Codex, OpenCode, OpenClaw, Hermes.
- **Insight**: richer (but still read-only) usage/cost analytics and session history.
- **Polish**: complete type coverage, broaden test coverage of the container path,
  and route library diagnostics through structured logging.

## Non-goals

- Re-implementing Claude Code's native todo, subagent, or session-resume features.
- A stateful, write-capable web UI. The ops console stays read-only; the CLI is the
  source of truth for changes.
