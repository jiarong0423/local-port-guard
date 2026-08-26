# Open Source Positioning

## Short Pitch

Local Port Guard is a safe local port and launchd service guardrail for developers who run long-lived local agents, dashboards, automation, and APIs on macOS.

## One-Line Description

Not a port killer: a local service guardrail that explains, protects, and verifies before stopping macOS listeners.

## Problem

Modern developer workstations increasingly behave like small servers. A single machine may run:

- dashboards
- read APIs
- browser automation profiles
- AI agents
- local proxy services
- mobile debugging daemons
- certificate signing bridges
- sync jobs
- scheduled launchd services

When the machine gets hot or ports are blocked, developers often reach for:

```bash
lsof -i :<port>
kill -9 <pid>
```

That is fast but risky. It does not answer:

- Is this a critical local service?
- Is this owned by launchd?
- Will it restart if killed?
- Is this a system service?
- Is this an app listener that should be quit instead of killed?
- Did the stop actually work?

## Existing Tools

Existing tools are useful but usually focus on one side of the problem.

### Port Tools

Examples:

- lsport
- portman
- Ports
- port-kill

They are good at listing ports and killing blocking processes. They are less focused on protected business services, launchd lifecycle decisions, and explanation-first operation.

### launchd Tools

Examples:

- launchd-ui
- LaunchMate
- Launchyard
- macos-zlaunch-manager

They are good at managing LaunchAgents and LaunchDaemons. They are not usually port-first and do not classify a listener based on why a developer sees it on a local port.

## Differentiation

Local Port Guard combines a port-first workflow with local service governance:

- classify before action
- explain before stop
- protected port allowlist
- launchd-aware stop planning
- system-service read-only policy
- unknown-service report-only policy
- post-stop verification
- local-only GUI
- AI-assisted operations compatibility

## Target Users

Primary users:

- developers running multiple local apps
- AI agent power users
- data pipeline operators
- quantitative trading or dashboard users
- people with always-on macOS workstations
- engineers who need safer local cleanup than one-click kill tools

Secondary users:

- support engineers
- SREs managing local development environments
- developers maintaining launchd jobs

## Product Boundary

Local Port Guard should stay narrow.

It should not become:

- a full observability suite
- a cloud monitoring platform
- a generic process manager
- an endpoint security product
- an automatic remediation agent

The correct product boundary is:

```text
local listener discovery
  + service classification
  + lifecycle-safe stop planning
  + protection rules
  + auditability
```

## Naming Options

Good names:

- Local Port Guard
- Port Sentinel
- Port Steward
- LaunchPort Guard
- PortSentry Local

The current working name is Local Port Guard because it describes the safety posture clearly.
