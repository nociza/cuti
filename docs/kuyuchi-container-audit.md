# Kuyuchi Container Audit and Split Proposal

Date: 2026-02-18

Related security gate: `docs/kuyuchi-threat-model.md`

## Scope

This audit covers:

- current `cuti` container behavior (`src/cuti/services/devcontainer.py`)
- current Clawdbot flow (`src/cuti/cli/commands/clawdbot.py`, `src/cuti/services/clawdbot_instance.py`)
- related docs (`docs/devcontainer.md`, `docs/clawdbot.md`, `docs/clawdbot-workspace-layout.md`)
- reusable open-source components for a hardened minimal Clawdbot runtime

## Current Setup: What Exists and Why

### Single image does everything

Current image (`cuti-dev-universal`) mixes both goals:

- cloud dev utility environment (Claude CLI, Docker CLI, Python, Node, shell tools)
- Clawdbot runtime (legacy sandbox install + gateway wrappers + workspace linking)

Why this exists:

- one command path (`cuti container`) for all workflows
- no extra image management
- easy host-to-container state persistence under `~/.cuti`

### Dockerfile sections and intent

1. Base + apt packages  
Purpose: general developer UX and broad compatibility.

2. Docker CLI + compose wrapper  
Purpose: allow Docker-in-Docker style usage by mounting host socket.

3. Node + pnpm + npm wrapper  
Purpose: support Claude/Clawdbot and Node tool installs; route npm commands through pnpm.

4. Claude CLI wrapper (`--dangerously-skip-permissions`)  
Purpose: keep Claude operational in container without interactive permission prompts.

5. Legacy Clawdbot sandbox install  
Purpose: keep the separate `cuti clawdbot` runtime self-contained without tying it to provider selection.

6. zsh/oh-my-zsh setup  
Purpose: interactive shell ergonomics.

### Runtime init script sections and intent

1. Workspace writability detection  
Purpose: avoid failures on read-only mounts; fallback storage paths.

2. Docker socket GID fixes/wrappers  
Purpose: keep `docker` commands working for non-root user in mixed host environments.

3. Claude config sync (`~/.claude` -> `~/.cuti/claude-linux`)  
Purpose: separate Linux credentials from macOS keychain behavior.

4. Clawdbot install/linking/wrappers  
Purpose: guarantee command availability and persistent config/workspace links.

5. `.cuti` shared mount symlink  
Purpose: make host `~/.cuti` the canonical long-lived storage.

## Findings: Why It Feels Bulky

1. **Goal collision in one runtime path**  
Cloud utility and sandboxed bot are contradictory profiles.

2. **Security posture is too broad for bot mode**  
Even with `mount_docker_socket=False`, Clawdbot still inherits:
- host network mode (`--network host`)
- broad host state mount (`~/.cuti` as a whole)
- large bootstrap logic with elevated operations (`sudo`, `chown`, socket handling)

3. **Operational bulk**  
- large base stack (Python + Node + Docker CLI + shell UX + extras)
- duplicated install behavior at build and startup
- startup script includes many unrelated concerns

4. **Docs drift**  
Some docs describe behavior that differs from code (example: claims about socket handling and privileges).

## Target Split: Two Explicit Container Products

## 1) `kuyuchi-cloud` (full cloud util)

Purpose:

- containerized Claude Code development workspace
- plugin/tool-heavy workflows
- optional Docker socket access for nested workflows

Characteristics:

- broad toolchain
- existing convenience behavior retained
- can keep host-network mode if required for developer convenience

## 2) `kuyuchi-clawdbot` (minimal sandbox runtime)

Purpose:

- run Clawdbot/OpenClaw bot safely with minimal blast radius
- strict workspace-scoped file access
- network access enabled for messaging providers
- browser automation/tool support for bot tasks

Characteristics:

- no Docker socket mount
- no global `~/.cuti` mount
- no host network mode by default
- rootless runtime and hardened container flags

## Hardened Clawdbot Runtime Baseline

Use this as minimum policy for bot mode:

- mount only:
  - target workspace (rw)
  - dedicated bot state dir (optional, explicit path; not whole home)
- runtime flags:
  - `--cap-drop=ALL`
  - `--security-opt=no-new-privileges:true`
  - `--pids-limit=256` (or tighter)
  - `--read-only` + `--tmpfs /tmp` + `--tmpfs /run`
  - optional: custom seccomp profile
- networking:
  - bridge networking + explicit `-p` mappings
  - no host network mode unless explicitly requested
- identity:
  - run as non-root user
- process control:
  - `--init`
  - no privileged mode

Recommended stronger isolation (optional):

- gVisor (`runsc`) runtime
- or Kata Containers if VM-backed isolation is desired

## Browser + Plugin Strategy for Bot Mode

Two safe options:

1. Built-in browser tool in sandbox  
Use OpenClaw/OpenClaw-like browser integration inside bot sandbox.

2. Remote browser service  
Run browser service in a separate container and connect via URL/token; bot container only gets network access to that endpoint.

## Reuse Candidates from Open Source

### OpenClaw ecosystem

- `openclaw/openclaw`:
  - sandbox modes (`workspace-write`, `read-only`, `all`, `none`)
  - workspace-only patterns
  - security policy engine (allow/deny + path regex)
  - browser tool and remote-browser integration

- `openclaw/openclaw-docker`:
  - production container/deploy patterns for OpenClaw server stacks

- `openclaw/lobster`:
  - endpoint + sandbox orchestration model for coding agents

- `openclaw/openclaw-ansible`:
  - infra automation patterns for multi-host deployments

### General isolation components

- gVisor (`runsc`) for syscall/kernal surface reduction
- Kata Containers for VM-level workload isolation
- Podman rootless mode for daemonless least-privilege operation

## Dashboard and Control Plane Direction

Current `cuti web` is a lightweight read-only ops console rather than a broad dashboard/control plane.

Recommended additions:

- Clawdbot runtime card:
  - running/stopped
  - active workspace path
  - current port mappings
  - network egress summary
- Policy card:
  - active sandbox mode
  - mounted paths (explicit)
  - security flags currently active
- Actions:
  - start/stop/restart bot runtime
  - rotate bot state directory
  - export incident bundle (logs + config snapshot sans secrets)

## Implementation Plan (Repository)

Phase 1 (lowest risk, immediate):

1. Introduce explicit runtime profiles in `DevContainerService`:
   - `cloud`
   - `clawdbot_sandbox`
2. Route `cuti clawdbot ...` to `clawdbot_sandbox` profile.
3. Remove host-network default for clawdbot profile.
4. Restrict mounts for clawdbot profile to workspace + explicit bot-state path.
5. Enforce no Docker socket mount for clawdbot profile.

Phase 2 (hardening):

1. Add hardened run args listed above.
2. Add seccomp profile file under `docker/seccomp/`.
3. Add container profile tests that assert docker args for each mode.

Phase 3 (operability):

1. Add dashboard panels for bot runtime and policy status.
2. Add bot health checks (gateway, channel connectivity, browser tool availability).
3. Add explicit audit log for start/stop/config changes.

## Acceptance Criteria

Cloud profile:

- still supports Claude + plugins + optional Docker socket workflows.

Clawdbot profile:

- cannot access host Docker daemon
- only sees allowed workspace/state mounts
- has outbound network for messaging providers
- supports browser tool path
- exposes controllable, observable status in dashboard
