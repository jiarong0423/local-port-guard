# Framework

This document describes the product framework for Local Port Guard.

## Product Goal

Local Port Guard helps developers decide whether a listening local port is safe to stop.

The tool is intentionally not a one-click port killer. It is a local service guardrail with classification, explanation, protection, launchd awareness, and post-action verification.

## System Framework

```mermaid
flowchart TB
  subgraph Inputs
    LSOF[lsof listeners]
    PS[ps process metadata]
    LC[launchctl state]
    Rules[Local rules]
  end

  subgraph DecisionCore[Decision Core]
    Normalize[Normalize listener rows]
    Enrich[Enrich process and launchd metadata]
    Classify[Classify service type]
    Risk[Assign stop policy and risk]
    Explain[Build human-readable explanation]
  end

  subgraph Outputs
    CLI[CLI report]
    JSON[JSON API]
    GUI[Local GUI]
    Skill[Codex skill context]
  end

  subgraph Actions
    DryRun[Dry-run stop plan]
    Confirm[Explicit confirmation]
    Stop[launchd-aware stop or TERM fallback]
    Verify[Rescan target port]
    Audit[Audit log]
  end

  LSOF --> Normalize
  PS --> Enrich
  LC --> Enrich
  Rules --> Classify
  Normalize --> Enrich
  Enrich --> Classify
  Classify --> Risk
  Risk --> Explain
  Explain --> CLI
  Explain --> JSON
  JSON --> GUI
  Explain --> Skill
  Risk --> DryRun
  DryRun --> Confirm
  Confirm --> Stop
  Stop --> Verify
  Verify --> Audit
```

## Classification Framework

```mermaid
flowchart LR
  Listener[Listening port] --> Exact{Exact port rule?}
  Exact -->|yes| PortRule[Apply port rule]
  Exact -->|no| Cmd{Command regex rule?}
  Cmd -->|yes| CommandRule[Apply command rule]
  Cmd -->|no| Unknown[unknown / report-only]

  PortRule --> Policy
  CommandRule --> Policy
  Unknown --> Policy

  Policy{Stop policy}
  Policy -->|blocked| Protected[Protected: refuse stop]
  Policy -->|readonly| ReadOnly[System: explanation only]
  Policy -->|report-only| ReportOnly[Visible, no stop action]
  Policy -->|confirm| Confirmable[Dry-run plan available]
```

## Stop Framework

```mermaid
sequenceDiagram
  participant User
  participant GUI
  participant CLI
  participant Policy
  participant OS

  User->>GUI: Select port
  GUI->>CLI: stop --port N
  CLI->>Policy: classify and plan
  Policy-->>CLI: dry-run plan or refusal
  CLI-->>GUI: explanation
  GUI-->>User: show plan
  User->>GUI: confirm
  GUI->>CLI: stop --port N --execute
  CLI->>Policy: re-check policy
  Policy-->>CLI: approved plan
  CLI->>OS: launchctl bootout or kill -TERM
  CLI->>OS: rescan port
  CLI-->>GUI: verification result
```

## Policy Matrix

| Category | Examples | Policy | Stop Strategy |
|---|---|---|---|
| `protected` | business-critical local API or dashboard | `blocked` | Refuse |
| `development` | Next.js, Vite, Rails, Django dev server | `confirm` | launchd if managed, else TERM |
| `signing` | HiPKI, TIPO ServiSign | `confirm` | launchd if managed, else TERM |
| `browser-tooling` | Chrome DevTools remote debugging | `confirm` | TERM specific debug profile |
| `mobile-dev` | ADB server | `confirm` | Prefer native stop command |
| `system` | ControlCenter, rapportd | `readonly` | No stop |
| `user-app` | LINE, Slack, Discord | `report-only` | No stop by default |
| `guard-tool` | Local Port Guard GUI | `report-only` | No stop by default |
| `unknown` | unmatched listener | `report-only` | No stop |

## Recommended Repository Shape

```text
local-port-guard/
  README.md
  LICENSE
  local_port_guard.py
  local_port_guard_gui.py
  docs/
    ARCHITECTURE.md
    ENGINEERING.md
    FRAMEWORK.md
    OPEN_SOURCE_POSITIONING.md
    ROADMAP.md
    SECURITY_MODEL.md
    TEST_PLAN.md
  codex-skill/
    SKILL.md
```

## Future Package Shape

When the prototype grows, split the code into modules:

```text
local_port_guard/
  __init__.py
  cli.py
  scanner.py
  metadata.py
  classifier.py
  policy.py
  stop_planner.py
  launchd.py
  audit.py
  config.py
  server.py
  static/
tests/
```

The current single-file prototype is intentional. It keeps the first open-source version easy to inspect.
