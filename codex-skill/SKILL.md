---
name: local-port-lifecycle-guard
description: Inspect and safely manage macOS local listening ports, launchd-backed services, and protected development ports such as local dashboards and APIs.
---

# Local Port Lifecycle Guard

Use this skill when the user asks to inspect local listening ports, explain what a port is doing, stop a local service, classify launchd jobs, or check whether protected local services are running.

## Local Invariants

- Treat configured protected ports as blocked by default. Do not stop them unless the user explicitly overrides protection in the same turn and names both the port and service.
- Example protected ports in the prototype are `3012` and `8012`; downstream users should customize these rules.
- For launchd-backed processes, inspect the launchd job before stopping. Prefer stopping the job with `launchctl bootout` instead of killing only the child process.
- For system-owned macOS services such as `ControlCenter` and `rapportd`, default to read-only explanation.

## Workflow

1. Scan listeners with `lsof -nP -iTCP -sTCP:LISTEN`.
2. For candidate PIDs, inspect command lines with `ps`.
3. If a service may be launchd-managed, inspect `launchctl list` or `launchctl print gui/<uid>/<label>`.
4. Classify the listener before taking action:
   - protected: configured protected ports.
   - development: Next.js, local dev servers.
   - signing: HiPKI or TIPO ServiSign.
   - browser-tooling: Chrome remote debugging.
   - mobile-dev: ADB.
   - system: Apple/system background services.
   - unknown: no known mapping.
5. Before stopping anything, report what it is, why it is running, whether launchd will restart it, and the exact stop command.
6. Stop only the explicitly requested port or label.
7. After stopping, rescan the target port and confirm whether it is still listening.
8. Recheck protected ports after unrelated stop actions when there is any risk of collateral impact.

## Helper

When available, use:

```bash
python3 local_port_guard.py scan
```

For a dry-run stop plan:

```bash
python3 local_port_guard.py stop --port <port>
```

Execute only after clear user authorization:

```bash
python3 local_port_guard.py stop --port <port> --execute
```
