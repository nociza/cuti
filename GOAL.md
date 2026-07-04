# Project Goals - CUTI Direction

## Primary Objective
Focus CUTI on provider-aware runtime setup, observability, and native-session coordination across Claude Code, Codex, OpenClaw, Hermes, and related CLIs. CUTI should not reimplement provider-owned agent loops, queues, todo systems, permissions, approvals, or background execution.

## Strategic Reframe
Claude Code now owns much more of the local autonomy surface through native permission modes, including auto mode. That weakens any CUTI thesis based on making Claude autonomous by bypassing approvals.

CUTI's stronger thesis is the runtime/control-plane layer around native providers:

- Reproducible local containers for provider CLIs
- Persistent auth, config, skills, and runtime installs
- Readiness, drift, and session visibility across providers
- Multi-session and worktree coordination without owning provider execution
- Turnkey OpenClaw deployment, gateway, channel, browser, plugin, voice, node, sandbox, cron, secrets, memory, and wiki operations

OpenClaw deployment support should be treated as the clearest differentiated wedge because OpenClaw has real runtime topology, gateway state, channel auth, plugins, devices, and operational drift that provider-native Claude auto mode does not address.

## Provider-Native Capabilities (Deprioritized in CUTI)
Based on current Claude Code and Codex capabilities, these should be treated as low priority or out-of-scope unless CUTI can add clear cross-provider value:

- Provider-native non-interactive execution, background tasks, and scheduled runs
- Provider-native todo tracking inside the SDK/agent loop
- Provider-native subagents, background agents, and agent/session views
- Provider-native session continuation/resume and local conversation history
- Provider-native hooks, permissions, approvals, MCP, skills, and slash-command surfaces

CUTI should integrate with these areas rather than duplicate them. Differentiated value should come from provider/runtime management, cross-provider observability, workspace drift detection, session inventory, worktree awareness, and normalized metadata.

## Priorities

### P0 - Differentiate CUTI
- [ ] Make OpenClaw deployment and operations the flagship differentiated path
- [ ] Make provider-aware containers reliable across Claude Code, Codex, OpenClaw, Hermes, and OpenCode
- [ ] Surface native provider readiness, auth/config state, and runtime drift in `cuti web`
- [ ] Ingest native provider session/task signals without owning execution
- [ ] Establish durable persistence for CUTI-specific provider/runtime metadata
- [ ] Detect workspace and worktree conflicts across concurrently running native sessions
- [ ] Prefer Claude native permission modes (`auto`, `acceptEdits`, `plan`) over CUTI-owned approval bypass behavior

### P1 - High-Value Integrations
- [ ] Capture and normalize Claude/Codex/OpenClaw progress signals for CUTI dashboards
- [ ] Link CUTI work items to provider-native session/task IDs when useful
- [ ] Implement interactive goal management with project-level views
- [ ] Add blocker detection and handoff workflows based on native provider outputs
- [ ] Add analytics for usage, throughput, blockers, completion quality, and provider readiness

### P2 - Legacy / Compatibility Only
- [ ] Keep existing queue commands working for current users, but do not treat the local queue as product strategy
- [ ] Avoid expanding the local todo system unless it becomes a provider-linked work item registry
- [ ] Avoid rebuilding generic subagent infrastructure
- [ ] Avoid rebuilding baseline session history/resume mechanisms
- [ ] Avoid rebuilding generic slash-command and hook frameworks

## Success Criteria

1. Functionality
   - CUTI launches and maintains provider-aware local runtimes reliably
   - Provider-native signals (sessions, todos, progress, events, tasks) are visible in CUTI dashboards
   - Any CUTI work item metadata links back to native provider sessions instead of replacing them

2. Performance
   - Sub-second status/telemetry refresh for active sessions
   - Handle 10+ active native sessions with stable observability behavior
   - Zero loss of CUTI-managed provider/runtime metadata on restart

3. Usability
   - Clear project/provider/session visibility without duplicating provider core UX
   - Fast path from project setup to native provider execution
   - Minimal manual coordination needed for multi-session workflows

## Phase Plan

- Phase 1: Provider runtime hardening + native session/task signal ingestion
- Phase 2: Real-time web sync + dashboarding + reliability hardening
- Phase 3: Multi-session/worktree conflict detection + handoff workflows
- Phase 4: Advanced analytics and provider-aware recommendations

## Notes

- Keep CUTI scope additive to native provider CLIs.
- Prefer integration points over feature duplication.
- Treat Claude permission bypass as an explicit compatibility escape hatch, not the product premise.
- Re-evaluate deprioritized items only if provider-native support drops or exposes gaps critical to CUTI use cases.

---
*Last Updated: 2026-07-03*
*Version: 1.3.0*
