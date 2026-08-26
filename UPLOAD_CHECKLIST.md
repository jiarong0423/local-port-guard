# GitHub Upload Checklist

Repository:

```text
https://github.com/<owner>/local-port-guard
```

## Files To Upload

- `README.md`
- `LICENSE`
- `.gitignore`
- `local_port_guard.py`
- `local_port_guard_gui.py`
- `docs/ARCHITECTURE.md`
- `docs/ENGINEERING.md`
- `docs/FRAMEWORK.md`
- `docs/OPEN_SOURCE_POSITIONING.md`
- `docs/ROADMAP.md`
- `docs/SECURITY_MODEL.md`
- `docs/TEST_PLAN.md`
- `codex-skill/SKILL.md`

## Suggested First Commit

```text
Initial Local Port Guard prototype
```

## Suggested GitHub Description

```text
A safe macOS local port and launchd service guardrail for developers.
```

## Suggested Topics

```text
macos
ports
launchd
developer-tools
local-first
python
gui
process-management
```

## Pre-Upload Validation

Run from this folder:

```bash
python3 -m py_compile local_port_guard.py local_port_guard_gui.py
python3 local_port_guard.py scan
python3 local_port_guard.py stop --port 3012
python3 local_port_guard.py stop --port 8012
```

Expected:

- syntax checks pass
- scan reports local listening ports
- protected ports refuse stop

## Known Prototype Limitations

- rules are still hard-coded
- audit log is not implemented yet
- GUI is a lightweight local web UI, not a packaged macOS app
- system service classification is conservative
- GitHub connector may not have push permission; upload can be done by local git or web UI
