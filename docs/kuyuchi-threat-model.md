# Kuyuchi Clawdbot Threat Model (Pre-Implementation)

Date: 2026-02-18  
Status: Draft, design gate for implementation  
Applies to: planned `kuyuchi-clawdbot` minimal runtime profile

Code mapping: `src/cuti/services/devcontainer.py` (`RUNTIME_SECURITY_CHECKLIST`, runtime profile validation, seccomp enforcement)

## 1. Purpose

Define a strict security model for the minimal Clawdbot/OpenClaw container so blast radius is limited to:

- the assigned workspace
- explicitly mounted bot state
- allowed network communication paths

This document is a security gate before code changes.

## 2. Security Objectives

### 2.1 Primary objectives

1. **Workspace confinement**  
Bot runtime can access only the mounted workspace plus explicit state path.

2. **Host protection**  
Bot runtime cannot control host Docker, host kernel, or host filesystem beyond allowed mounts.

3. **Network-enabled operation**  
Bot runtime can reach required messaging/broker/provider endpoints.

4. **Operational control and visibility**  
Operators can monitor runtime policy state, active mounts, and runtime health in dashboard.

### 2.2 Non-objectives

- Preventing all outbound data exfiltration from compromised bot logic (this requires endpoint-specific egress policy and DLP, not just container isolation).
- Protecting against full host root compromise outside container runtime guarantees.

## 3. System Under Review

Current behavior (from repository):

- Unified container path for cloud util and Clawdbot (`src/cuti/services/devcontainer.py`).
- `cuti clawdbot` disables Docker socket mount (`src/cuti/cli/commands/clawdbot.py:428`), but still reuses broad runtime path.
- Runtime still uses host network (`src/cuti/services/devcontainer.py:750`) and mounts host `~/.cuti` wholesale (`src/cuti/services/devcontainer.py:736`).
- Bootstrap script includes privileged setup steps (`sudo`, socket permission mutation, ownership rewrites) in `src/cuti/services/devcontainer.py:808` and `src/cuti/services/devcontainer.py:1056`.

Security implication:

- Current clawdbot path has reduced host-Docker exposure compared with full cloud mode, but is not minimal-isolation.

## 4. Assets and Classification

| Asset | Examples | Classification | Security need |
|---|---|---|---|
| Host system control plane | Docker daemon/socket, kernel interfaces | Critical | Must be unreachable |
| Host filesystem outside workspace | home dir, SSH keys, credentials | Critical | Must be unreachable |
| Bot credentials/secrets | channel tokens, OAuth artifacts | High | Confidentiality + integrity |
| Workspace files | project code/data | High | Integrity + scoped confidentiality |
| Runtime policy metadata | mounts, flags, active profile | Medium | Integrity + operator visibility |
| Runtime logs | gateway logs, security/audit events | Medium | Integrity + retention |

## 5. Trust Boundaries

1. **Host OS / Docker runtime boundary**  
Untrusted bot execution must not cross into host control plane.

2. **Container filesystem boundary**  
Only explicit bind mounts are trusted exposure points.

3. **Network boundary**  
Outbound traffic required; ingress should be explicit and minimal.

4. **Control plane boundary**  
Dashboard/CLI actions that start/stop/configure runtime must be authenticated and auditable.

## 6. Threat Actors and Capabilities

1. **Malicious prompt input / remote message sender**  
Can induce arbitrary tool and shell actions through agent behavior.

2. **Compromised plugin or tool dependency**  
Executes arbitrary code inside bot runtime.

3. **Curious insider with project access**  
Tries to pivot from workspace to host/system controls.

4. **External network attacker**  
Targets exposed ports/services or browser automation endpoints.

## 7. Entry Points and Attack Surface

1. Clawdbot command execution path (`cuti clawdbot ...`).
2. Container runtime flags and mounts (`docker run` arguments).
3. Plugin/tool install and execution chain.
4. Browser automation subsystem (local browser or remote browser endpoint).
5. Gateway/network listeners and control UI ports.
6. State/config directories and symlink/link logic.

## 8. Abuse Cases (What Must Be Prevented)

1. **Host Docker takeover**  
Attacker reaches `/var/run/docker.sock` and starts privileged host containers.

2. **Filesystem breakout via broad mounts**  
Attacker reads secrets outside assigned workspace.

3. **Container escape amplification**  
Excess Linux capabilities or permissive seccomp enables kernel attack primitives.

4. **Network pivot through host mode**  
Host network exposure increases lateral movement and service discovery.

5. **Plugin supply-chain execution with high privileges**  
Dependency script executes with unnecessary privileges, modifies runtime policy.

6. **Browser tool abuse**  
Automated browser channel used to exfiltrate secrets from internal resources.

7. **Silent policy drift**  
Runtime starts without expected hardening flags and operators cannot detect it.

## 9. Threat Analysis (STRIDE-Oriented)

| Threat | Category | Current exposure | Required control | Detection |
|---|---|---|---|---|
| Start sibling containers via host daemon | EoP | Reduced for clawdbot path; still mixed runtime | Never mount Docker socket in sandbox profile | Startup policy check + runtime probe |
| Read host files outside workspace | Info disclosure | Broad `.cuti` mount today | Workspace + explicit state-only mounts | Mount inventory endpoint |
| Modify runtime policy without trace | Tampering/Repudiation | Limited audit trail | Immutable profile + signed config + audit log | Dashboard + append-only audit feed |
| Kernel attack via extra caps/syscalls | EoP | Not fully minimized | `cap_drop=ALL`, seccomp, no-new-privileges, rootless | Runtime introspection endpoint |
| Lateral scan/pivot using host network | Info disclosure/Tampering | `--network host` currently | Bridge network + explicit port mappings | Connection metrics + denied-flow logs |
| Plugin/postinstall compromise | Tampering | Toolchain broad and dynamic | Allowlisted plugins, checksum lock, separate build stage | Plugin provenance records |
| Browser endpoint misuse | Info disclosure | Depends on implementation | Browser in separate sandbox or remote service with auth | Browser session/audit logs |

## 10. Mandatory Security Invariants

The minimal clawdbot profile must satisfy all invariants:

1. `/var/run/docker.sock` is not mounted.
2. Only approved mounts exist:
   - `/workspace` (rw)
   - `/state` (rw, optional but explicit)
   - no host home root mount
3. Container runs as non-root user.
4. Capabilities: none beyond baseline (`cap_drop=ALL`).
5. `no-new-privileges` is enabled.
6. Root filesystem is read-only; writable temp via tmpfs.
7. Network mode is not host; ingress only via explicit mapped ports.
8. Policy/mount/runtime settings are observable from dashboard/CLI.

If any invariant fails, runtime start must fail closed.

## 11. Required Control Set

### 11.1 Runtime isolation

- `--cap-drop=ALL`
- `--security-opt=no-new-privileges:true`
- `--read-only`
- `--tmpfs /tmp:rw,noexec,nosuid,nodev`
- `--tmpfs /run:rw,nosuid,nodev`
- `--pids-limit` and memory/cpu limits
- non-root `--user`
- optional hardening tier:
  - custom seccomp profile
  - AppArmor/SELinux profile
  - gVisor/Kata runtime class

### 11.2 Mount policy

- Allowed mounts only:
  - workspace path
  - dedicated clawdbot state path
- Disallowed:
  - host home directory root mounts
  - Docker socket
  - broad host config mounts unrelated to bot runtime

### 11.3 Network policy

- bridge mode by default (no host network)
- explicit `-p` for UI/gateway if needed
- optional egress allowlist for messaging providers and bot backends
- optional DNS restrictions for high-security mode

### 11.4 Plugin/tool policy

- allowlisted plugin set
- pinned versions/checksums
- plugin install/build in isolated build stage, not at runtime bootstrap
- disable arbitrary runtime package install in production mode

### 11.5 Secrets policy

- no secrets in image layers
- mount secrets as files/env only when needed
- rotateable bot state path and credential revocation path
- redact secrets from logs/events

### 11.6 Observability and control plane

- dashboard endpoints for:
  - active profile
  - effective mounts
  - effective security flags/capabilities
  - process/resource/network summary
- append-only audit records for:
  - profile changes
  - runtime start/stop/restart
  - config changes
  - policy violations

## 12. Verification Plan (Pass/Fail Security Tests)

Run these against clawdbot profile on every release:

1. **No Docker socket test**  
Inside container: `/var/run/docker.sock` absent -> pass.

2. **Mount confinement test**  
Inside container cannot read host paths outside mounts -> pass.

3. **Capability drop test**  
`capsh --print` (or equivalent) confirms no elevated caps -> pass.

4. **No-new-privileges test**  
Runtime inspect confirms `NoNewPrivileges=true` -> pass.

5. **Read-only rootfs test**  
Write to `/usr` fails; write to `/tmp` succeeds -> pass.

6. **Network mode test**  
Inspect confirms non-host network mode -> pass.

7. **Ingress exposure test**  
Only explicitly mapped ports reachable from host -> pass.

8. **Policy introspection test**  
Dashboard/CLI shows effective runtime policy and mounts -> pass.

9. **Audit trail test**  
Start/stop/config events appear with timestamps and actor/source -> pass.

## 13. Residual Risks

1. **Application-level exfiltration**  
Even with strong container isolation, bot logic can exfiltrate workspace data over allowed network.

2. **Zero-day container/runtime escape**  
Mitigated but not eliminated; stronger runtime isolation reduces impact.

3. **Operator misconfiguration**  
Wrong profile or custom run args can weaken controls unless fail-closed validation exists.

## 14. Incident Response Requirements

Minimum response workflow:

1. Stop affected clawdbot runtime(s).
2. Snapshot logs + policy + config metadata (secrets redacted).
3. Revoke/rotate channel/provider credentials.
4. Recreate runtime from known-good profile.
5. Review audit timeline and tighten policy gaps.

## 15. Mapping to Planned Implementation

From `docs/kuyuchi-container-audit.md`, implementation phases should satisfy this model:

- Phase 1: profile split and mount/network separation.
- Phase 2: hardening flags + seccomp + tests.
- Phase 3: dashboard policy visibility + auditability.

No phase can be considered complete unless section 10 invariants and section 12 tests pass.
