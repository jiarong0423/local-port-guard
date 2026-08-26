# Architecture

Local Port Guard is designed around one rule: stopping a local listener is a lifecycle decision, not a raw PID operation.

## Layers

### Scanner

The scanner collects listening TCP sockets with:

```bash
lsof -nP -iTCP -sTCP:LISTEN
```

The scanner groups results by PID and port so IPv4 and IPv6 duplicates can be represented as one logical listener when appropriate.

### Metadata Enrichment

The metadata layer enriches listener rows with:

- parent PID
- CPU percentage
- memory percentage
- elapsed runtime
- full command line
- launchd label

The prototype uses:

```bash
ps -p <pid-list> -o pid=,ppid=,pcpu=,pmem=,etime=,command=
launchctl list
```

If `ps` or `launchctl` is unavailable or blocked by a sandbox, the scanner degrades gracefully and still reports the lsof-derived listener set.

### Classifier

The classifier applies two rule types:

- exact port rules
- command regex rules

Exact port rules are used for local invariants such as protected dashboard or API ports. Command regex rules are used for service families such as signing bridges, Next.js, Chrome remote debugging, and desktop apps.

Each classified listener receives:

- category
- display name
- explanation
- launchd label hint
- stop policy

### Stop Planner

The stop planner refuses protected and read-only services. For stoppable services, it builds an explicit plan.

If a launchd label exists, the plan uses:

```bash
launchctl bootout gui/<uid>/<label>
```

If no launchd label exists, the plan falls back to:

```bash
kill -TERM <pid>
```

The planner does not execute by default. The CLI requires `--execute`, and the GUI requires a confirmation step.

### Verifier

After a stop action, the verifier rescans the target port. The stop is successful only if the target port is no longer listening.

## GUI

The GUI is a local-only web interface served by Python's standard library HTTP server.

```text
Browser
  -> http://127.0.0.1:8765
  -> /api/scan
  -> /api/stop
  -> CLI subprocess
```

The GUI does not implement its own stop logic. It delegates to the CLI so the same safety policy is enforced in both modes.

## Data Flow

```text
lsof
  -> listeners
  -> ps metadata
  -> launchctl metadata
  -> classifier
  -> report JSON
  -> CLI text report or GUI table

stop request
  -> rescan target
  -> classify target
  -> policy check
  -> stop plan
  -> optional execute
  -> post-stop rescan
```

## Error Handling

The prototype treats missing or blocked metadata commands as degraded mode, not fatal failure.

Expected degraded cases:

- sandbox blocks `ps`
- sandbox blocks `launchctl`
- command not found
- listener exits between lsof and ps

The tool still reports the port, PID, process name, category where possible, and stop policy.

## Future Architecture

The open-source version should separate the code into modules:

```text
local_port_guard/
  scanner.py
  metadata.py
  classifier.py
  launchd.py
  stop_planner.py
  audit.py
  config.py
  server.py
  static/
```

This split is not required for the prototype, but it will make testing and packaging cleaner.
