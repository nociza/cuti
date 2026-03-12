# Project Goals - CUTI Enhancement

## Primary Objective
Focus CUTI on orchestration, observability, and multi-session coordination on top of Claude Code, not re-implementing core Claude Code capabilities.

## Claude Code Native Capabilities (Deprioritized in CUTI)
Based on current Anthropic Claude Code docs and release notes, these are already first-class features in Claude Code and should be treated as low priority or out-of-scope in CUTI:

- Native todo tracking in the SDK/agent loop (deprioritize building a parallel base todo engine)
- Built-in subagents (`/agents`) with separate context windows (deprioritize baseline multi-agent primitives)
- Built-in session continuation/resume (`--continue`, `--resume`) and local conversation history (deprioritize raw session persistence features)
- Built-in hooks lifecycle and permissions controls (deprioritize generic tool-level policy framework duplication)
- Built-in slash commands for config/review/status/memory/mcp/cost (deprioritize command-surface parity work)

CUTI should only extend these areas where we add differentiated value (cross-session orchestration, queue semantics, analytics, team workflows, container/runtime management).

## Priorities

### P0 - Differentiate CUTI
- [ ] Build robust queue system for task distribution across sessions/workspaces
- [ ] Create real-time sync between Claude Code runs and cuti web interface
- [ ] Establish durable persistence for cuti-specific orchestration state
- [ ] Build comprehensive analytics dashboard (usage, throughput, blockers, completion quality)
- [ ] Implement conflict-aware orchestration for concurrent agent/session execution

### P1 - High-Value Integrations
- [ ] Capture and normalize Claude todo/progress signals for cuti dashboards
- [ ] Create agent/session-specific task assignment and routing on top of Claude subagents
- [ ] Implement interactive goal management with project-level views
- [ ] Add automated blocker detection and escalation workflows

### P2 - Deprioritized (Claude Code already covers baseline)
- [ ] Rebuilding generic todo tracking primitives already provided by Claude Code
- [ ] Rebuilding generic subagent infrastructure already provided by Claude Code
- [ ] Rebuilding baseline session history/resume mechanisms
- [ ] Rebuilding generic slash-command and hook frameworks

## Success Criteria

1. Functionality
   - CUTI orchestrates multiple Claude sessions/workspaces reliably
   - Claude-native signals (todos/progress/events) are visible in CUTI dashboards
   - Queue and routing decisions are transparent and auditable

2. Performance
   - Sub-second status/telemetry refresh for active sessions
   - Handle 10+ active Claude sessions with stable orchestration behavior
   - Zero loss of CUTI-managed orchestration metadata on restart

3. Usability
   - Clear project/goal/task visibility without duplicating Claude core UX
   - Fast path from goal definition to queued executable work
   - Minimal manual coordination needed for multi-session workflows

## Phase Plan

- Phase 1: Queue + orchestration persistence + Claude signal ingestion
- Phase 2: Real-time web sync + dashboarding + reliability hardening
- Phase 3: Multi-session orchestration policies + conflict resolution
- Phase 4: Advanced analytics and predictive assistance

## Notes

- Keep CUTI scope additive to Claude Code.
- Prefer integration points over feature duplication.
- Re-evaluate deprioritized items only if Claude Code drops support or exposes gaps critical to CUTI use cases.

---
*Last Updated: 2026-03-12*
*Version: 1.1.0*
