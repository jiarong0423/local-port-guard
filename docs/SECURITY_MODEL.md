# Security Model

Local Port Guard is built for machines where local services may be important. The default posture is defensive.

## Principles

### Read-Only First

Scanning is always safe by default. The CLI `scan` command performs no mutation.

The GUI also starts in scan mode and does not execute stop actions without an explicit user action.

### Protected Services Cannot Be Stopped

Protected ports receive `stop_policy=blocked`.

In the current prototype:

- `3012` is protected.
- `8012` is protected.

Stop requests for protected ports are refused by the CLI layer, not only hidden in the GUI.

### System Services Are Read-Only

Known macOS system services such as ControlCenter and rapportd receive `stop_policy=readonly`.

The tool explains them but does not offer a stop action.

### Unknown Services Are Report-Only

Unknown listeners receive `stop_policy=report-only`.

This avoids stopping new or poorly understood services based only on a port number.

### Explicit Execution Required

The CLI stop command defaults to dry-run:

```bash
python3 local_port_guard.py stop --port 9222
```

Actual execution requires:

```bash
python3 local_port_guard.py stop --port 9222 --execute
```

The GUI first fetches the stop plan, then asks for confirmation, then sends a POST request with `execute=1`.

### launchd-Aware Lifecycle

For launchd-backed services, killing only the child process can be misleading. It may restart immediately.

When a launchd label is detected, the planned stop operation is:

```bash
launchctl bootout gui/<uid>/<label>
```

Only when no launchd label is known does the planner fall back to:

```bash
kill -TERM <pid>
```

### Post-Stop Verification

Every executed stop action is followed by a rescan of the target port. If the port is still listening, the tool reports verification failure.

## Threat Model

### In Scope

- accidental termination of critical local services
- launchd-managed service restart loops
- confusing stale PID/port state
- unknown listeners on developer machines
- misidentifying business-critical local APIs as disposable dev servers

### Out of Scope

- malware detection
- kernel-level monitoring
- network intrusion detection
- cloud security monitoring
- automatic remediation without user approval

## Localhost Binding

The GUI binds to:

```text
127.0.0.1
```

It should not bind to `0.0.0.0` by default.

## Audit Log Requirement

The prototype does not yet persist audit logs. The open-source version should record every stop plan and execution:

- timestamp
- command source
- target port
- PID
- command line
- launchd label
- category
- policy
- dry-run or execute
- command executed
- exit code
- verification result

## Administrative Privileges

The prototype does not attempt privilege escalation. If a stop action fails because the OS denies permission, it reports the failure.

Future versions may support privileged operations, but they should remain opt-in and should never bypass protected or read-only policies.
