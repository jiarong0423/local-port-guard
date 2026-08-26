# Engineering Guide

This document describes how Local Port Guard should be engineered as an open-source project.

## Engineering Priorities

1. Safety before convenience.
2. Deterministic local behavior before AI-generated advice.
3. Read-only by default.
4. Explicit user confirmation before mutation.
5. No hidden background cleanup.
6. No network dependency for core functionality.

## Current Implementation

The prototype has two executable files:

- `local_port_guard.py`
- `local_port_guard_gui.py`

The CLI owns the safety logic. The GUI delegates to the CLI instead of duplicating stop behavior.

This is intentional. Frontend code should never be the only enforcement layer for destructive operations.

## Command Dependencies

The macOS prototype uses:

- `lsof`
- `ps`
- `launchctl`
- `kill`

Optional future service-specific commands:

- `adb kill-server` for Android Debug Bridge
- `osascript` or application-specific quit flows for GUI apps

## Failure Handling

### Scanner Failures

If `lsof` fails, scanning cannot continue.

If `ps` fails, scanning should continue in degraded mode:

- PID remains available from `lsof`.
- CPU and memory may be unavailable.
- full command may be unavailable.

If `launchctl` fails, scanning should continue in degraded mode:

- launchd labels may be unavailable.
- protected port rules must still apply.

### Stop Failures

Stop execution must report:

- command attempted
- exit code
- stderr when available
- verification result

The tool must not silently escalate from `TERM` to `KILL`.

## Safety Invariants

These invariants should be covered by tests:

- Protected ports cannot be stopped.
- System services cannot be stopped.
- Unknown services cannot be stopped by default.
- GUI stop actions must pass through CLI policy.
- Stop execution must rescan the target port.
- Policy must be re-evaluated immediately before execution.

## Code Organization

The prototype is single-file for easy review. The first refactor should create this package shape:

```text
local_port_guard/
  scanner.py
  metadata.py
  rules.py
  classifier.py
  policy.py
  planner.py
  executor.py
  audit.py
  server.py
```

Suggested responsibilities:

| Module | Responsibility |
|---|---|
| `scanner.py` | run and parse lsof |
| `metadata.py` | process and launchd enrichment |
| `rules.py` | load and validate rules |
| `classifier.py` | assign category and name |
| `policy.py` | decide blocked, readonly, report-only, confirm |
| `planner.py` | build dry-run stop plan |
| `executor.py` | execute approved plan |
| `audit.py` | append structured audit logs |
| `server.py` | local GUI HTTP API |

## Configuration Design

Rules should move from source code into a config file.

Proposed default config:

```json
{
  "protected_ports": [3012, 8012],
  "port_rules": {
    "3012": {
      "category": "protected",
      "name": "Protected local dashboard",
      "stop_policy": "blocked"
    }
  },
  "command_rules": [
    {
      "pattern": "HiPKILocalSignServer|hipkiLocalServer",
      "category": "signing",
      "name": "HiPKI local signing server",
      "stop_policy": "confirm"
    }
  ]
}
```

Invalid configuration should fail closed. If the tool cannot parse policy, it should scan but refuse stop execution.

## GUI Requirements

The GUI should remain local-only.

Required behavior:

- bind to `127.0.0.1`
- show protected ports clearly
- disable stop for blocked, readonly, and report-only services
- show dry-run plan before confirmation
- rescan after stop
- never embed shell execution in frontend code

## Audit Logging

Audit logs should be JSON Lines.

Example event:

```json
{
  "timestamp": "2026-08-26T16:00:00+08:00",
  "action": "stop",
  "mode": "execute",
  "port": 9222,
  "pid": 12345,
  "category": "browser-tooling",
  "policy": "confirm",
  "launchd_label": null,
  "command": "kill -TERM 12345",
  "exit_code": 0,
  "verification": "stopped"
}
```

## Release Gate

Before release:

1. Run Python syntax checks.
2. Run CLI scan.
3. Run protected stop dry-runs for protected ports.
4. Start GUI.
5. Check `/api/scan`.
6. Check protected `/api/stop`.
7. Confirm README and docs match current behavior.

Minimum commands:

```bash
python3 -m py_compile local_port_guard.py local_port_guard_gui.py
python3 local_port_guard.py scan
python3 local_port_guard.py stop --port 3012
python3 local_port_guard.py stop --port 8012
```

## Open Questions

- Should service-specific stop handlers be opt-in?
- Should GUI support editing protected ports in v1?
- Should the first distributable be a Python package or Homebrew formula?
- Should remote SSH scanning be excluded from the first public release to keep the safety model narrow?
