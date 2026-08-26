# Roadmap

## Stage 0: Prototype

Status: complete.

Capabilities:

- CLI scan
- CLI guarded stop dry-run
- CLI guarded stop execute
- local web GUI
- hard-protected example local service ports
- basic service classification
- launchd label hints
- post-stop verification

## Stage 1: GitHub-Ready Repository

Goals:

- place source code in a package layout
- add README
- add architecture document
- add security model
- add roadmap
- add license
- add test plan
- add `.gitignore`

Exit criteria:

- a new user can understand what the tool does in under two minutes
- a developer can run the CLI without editing source code
- protected-port behavior is documented
- safety boundaries are explicit

## Stage 2: Configurable Rules

Move local rules out of source code.

Priority: highest next milestone.

Reason: the prototype already proves the safety model, but open-source users need to protect their own ports without editing Python source code.

Add:

```text
config/rules.example.json
~/.local-port-guard/rules.json
```

Rule types:

- protected ports
- exact port classifications
- command regex classifications
- launchd label classifications
- read-only system labels

Exit criteria:

- users can protect their own ports without editing Python
- default rules still protect known safe examples
- invalid config fails closed

## Stage 3: Audit Log

Add persistent operation logs.

Record:

- timestamp
- mode
- target port
- PID
- command
- launchd label
- category
- stop policy
- stop plan
- execution result
- verification result

Exit criteria:

- every stop request is traceable
- dry-run and execute events are both logged
- log path is documented

## Stage 4: launchd Detail View

Add structured launchd inspection.

Display:

- state
- plist path
- RunAtLoad
- KeepAlive
- stdout path
- stderr path
- last exit code
- runs
- PID
- domain

Exit criteria:

- user can see why a process would restart
- GUI differentiates user agents from system daemons
- system-level items remain read-only

## Stage 5: Tests

Add unit tests and command fixture tests.

Required test cases:

- protected ports cannot be stopped
- system services are read-only
- unknown listeners are report-only
- launchd-backed services produce a launchctl plan
- non-launchd stoppable services produce a TERM plan
- scanner tolerates blocked `ps`
- scanner tolerates missing `launchctl`
- GUI stop endpoint refuses protected ports

Exit criteria:

- tests pass on macOS CI or documented local test flow
- critical safety policy is covered

## Stage 6: GUI Hardening

Add:

- editable protected port list
- confirmation phrase for high-risk stops
- dry-run plan panel
- audit history panel
- launchd detail panel
- risk score

Exit criteria:

- GUI exposes the same safety policy as CLI
- no destructive action exists only in frontend code
- all stop actions pass through the CLI policy layer

## Stage 7: Packaging

Packaging options:

- Python package
- Homebrew formula
- standalone macOS app
- Tauri or SwiftUI wrapper

Preferred sequence:

1. Python package.
2. Homebrew formula.
3. Native menu bar app only if there is sustained usage.

## Stage 8: AI-Assisted Operations

Add structured output optimized for AI tools:

- JSON schema
- risk explanation fields
- recommended action
- refusal reason
- audit summary

This should stay advisory. AI should not bypass the stop policy.
