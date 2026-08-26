# Test Plan

## Safety Tests

### Protected Port Refusal

Command:

```bash
python3 local_port_guard.py stop --port 3012
python3 local_port_guard.py stop --port 8012
```

Expected:

- exit code is non-zero
- output contains `decision: refused`
- no stop command is executed

### System Service Read-Only

Command:

```bash
python3 local_port_guard.py stop --port 5000
python3 local_port_guard.py stop --port 7000
python3 local_port_guard.py stop --port 49152
```

Expected:

- stop is refused
- policy is `readonly`

### Unknown Service Report-Only

When a listener has no matching rule, expected:

- category is `unknown`
- policy is `report-only`
- GUI does not enable the stop button

## Stop Planning Tests

### launchd-Backed Service

For a listener with launchd label, dry-run output should include:

```bash
launchctl bootout gui/<uid>/<label>
```

### Non-launchd Service

For a listener without launchd label and policy `confirm`, dry-run output should include:

```bash
kill -TERM <pid>
```

## Degraded Environment Tests

### `ps` Permission Denied

Simulate or run in a sandbox where `ps` is blocked.

Expected:

- scan still succeeds
- CPU, memory, parent PID, and full command may be unavailable
- exact port rules still classify known ports

### `launchctl` Unavailable

Simulate missing launchctl.

Expected:

- scan still succeeds
- launchd label may be unavailable
- protected rules still apply

## GUI Tests

### Scan API

Command:

```bash
curl -sS http://127.0.0.1:8765/api/scan
```

Expected:

- JSON array
- protected ports are marked `blocked`

### Protected Stop API

Command:

```bash
curl -sS 'http://127.0.0.1:8765/api/stop?port=3012'
```

Expected:

- response includes `decision: refused`

### Homepage

Command:

```bash
curl -sS -I http://127.0.0.1:8765/
```

Expected:

- `200 OK`

## Manual QA

Before public release:

- verify GUI table on Safari and Chrome
- verify mobile-width layout
- verify stop button disabled for protected, readonly, report-only services
- verify stop confirmation contains the dry-run plan
- verify scan refresh after stop
