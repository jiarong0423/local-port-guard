#!/usr/bin/env python3
"""
Local Port Guard

Read-only by default. Scans macOS listening TCP ports, classifies them, maps
common launchd jobs, and optionally stops explicitly selected non-protected
services after showing the exact action plan.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any


PROTECTED_PORTS = {3012, 8012}

KNOWN_SERVICES = {
    3012: {
        "category": "protected",
        "name": "Protected local dashboard",
        "reason": "Example protected local dashboard port. Customize this rule for your own services.",
        "launchd_label": None,
        "stop_policy": "blocked",
    },
    8012: {
        "category": "protected",
        "name": "Protected local API",
        "reason": "Example protected local API port. Customize this rule for your own services.",
        "launchd_label": None,
        "stop_policy": "blocked",
    },
    3000: {
        "category": "development",
        "name": "Next.js local dev",
        "reason": "Common local development server. Stop only when not actively testing.",
        "stop_policy": "confirm",
    },
    3001: {
        "category": "development",
        "name": "Next.js local dev alternate",
        "reason": "Common alternate local development server. Stop only when not actively testing.",
        "stop_policy": "confirm",
    },
    5037: {
        "category": "mobile-dev",
        "name": "Android Debug Bridge",
        "reason": "ADB server for Android devices or emulators.",
        "stop_policy": "confirm",
    },
    9222: {
        "category": "browser-tooling",
        "name": "Chrome remote debugging",
        "reason": "Chrome DevTools Protocol port, often used by browser automation.",
        "stop_policy": "confirm",
    },
    8765: {
        "category": "guard-tool",
        "name": "Local Port Guard GUI",
        "reason": "This tool's localhost web interface.",
        "stop_policy": "report-only",
    },
    49152: {
        "category": "system",
        "name": "rapportd",
        "reason": "Apple continuity service used by Handoff/AirDrop-style features.",
        "stop_policy": "readonly",
    },
    5000: {
        "category": "system",
        "name": "ControlCenter",
        "reason": "macOS Control Center local listener.",
        "stop_policy": "readonly",
    },
    7000: {
        "category": "system",
        "name": "ControlCenter",
        "reason": "macOS Control Center local listener.",
        "stop_policy": "readonly",
    },
}

COMMAND_RULES = [
    (
        re.compile(r"HiPKILocalSignServer|hipkiLocalServer", re.I),
        {
            "category": "signing",
            "name": "HiPKI local signing server",
            "reason": "Local certificate/signature bridge, commonly used by Taiwan government certificate flows.",
            "launchd_label": "com.node.HIPKILocalServer.cht",
            "stop_policy": "confirm",
        },
    ),
    (
        re.compile(r"/Library/TIPO/ServiSign|ServiSign\.jar", re.I),
        {
            "category": "signing",
            "name": "TIPO ServiSign",
            "reason": "Taiwan Intellectual Property Office signing component for patent/IP electronic filing flows.",
            "launchd_label": "com.changing.servisign.tipo",
            "stop_policy": "confirm",
        },
    ),
    (
        re.compile(r"next-server|next dev", re.I),
        {
            "category": "development",
            "name": "Next.js local development server",
            "reason": "Local web development server.",
            "stop_policy": "confirm",
        },
    ),
    (
        re.compile(r"Google Chrome.*--remote-debugging-port", re.I),
        {
            "category": "browser-tooling",
            "name": "Chrome remote debugging",
            "reason": "Browser automation or debugging endpoint.",
            "stop_policy": "confirm",
        },
    ),
    (
        re.compile(r"/Applications/LINE\.app|(^|\s)LINE($|\s)", re.I),
        {
            "category": "user-app",
            "name": "LINE desktop app",
            "reason": "LINE desktop application local listener.",
            "stop_policy": "report-only",
        },
    ),
]


@dataclass
class Listener:
    port: int
    protocol: str
    command: str
    pid: int
    user: str
    addresses: set[str] = field(default_factory=set)
    ppid: int | None = None
    cpu: float | None = None
    mem: float | None = None
    etime: str | None = None
    full_command: str | None = None
    launchd_label: str | None = None
    category: str = "unknown"
    name: str = "Unknown listener"
    reason: str = "No local rule matched this listener."
    stop_policy: str = "report-only"


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, check=False)
    except PermissionError as exc:
        return subprocess.CompletedProcess(args, 126, "", str(exc))
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def parse_lsof_line(line: str) -> tuple[str, int, str, str, str] | None:
    parts = line.split()
    if len(parts) < 9:
        return None
    command = parts[0]
    try:
        pid = int(parts[1])
    except ValueError:
        return None
    user = parts[2]
    protocol = parts[7]
    name = " ".join(parts[8:])
    return command, pid, user, protocol, name


def extract_port(name: str) -> int | None:
    match = re.search(r":(\d+)\s+\(LISTEN\)$", name)
    if not match:
        return None
    return int(match.group(1))


def scan_lsof() -> list[Listener]:
    result = run_command(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "lsof failed")

    listeners: dict[tuple[int, int], Listener] = {}
    for line in result.stdout.splitlines()[1:]:
        parsed = parse_lsof_line(line)
        if not parsed:
            continue
        command, pid, user, protocol, name = parsed
        port = extract_port(name)
        if port is None:
            continue
        key = (pid, port)
        listener = listeners.get(key)
        if listener is None:
            listener = Listener(
                port=port,
                protocol=protocol,
                command=command,
                pid=pid,
                user=user,
            )
            listeners[key] = listener
        listener.addresses.add(name.replace(" (LISTEN)", ""))
    return sorted(listeners.values(), key=lambda item: (item.port, item.pid))


def load_ps_info(pids: list[int]) -> dict[int, dict[str, Any]]:
    if not pids:
        return {}
    result = run_command(
        [
            "ps",
            "-p",
            ",".join(str(pid) for pid in sorted(set(pids))),
            "-o",
            "pid=,ppid=,pcpu=,pmem=,etime=,command=",
        ]
    )
    if result.returncode != 0:
        return {}

    rows: dict[int, dict[str, Any]] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=5)
        if len(parts) < 6:
            continue
        try:
            pid = int(parts[0])
            rows[pid] = {
                "ppid": int(parts[1]),
                "cpu": float(parts[2]),
                "mem": float(parts[3]),
                "etime": parts[4],
                "full_command": parts[5],
            }
        except ValueError:
            continue
    return rows


def load_launchd_pid_map() -> dict[int, str]:
    result = run_command(["launchctl", "list"])
    if result.returncode != 0:
        return {}

    mapping: dict[int, str] = {}
    for line in result.stdout.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        pid_text, _status, label = parts
        if pid_text.isdigit():
            mapping[int(pid_text)] = label
    return mapping


def apply_metadata(listeners: list[Listener]) -> None:
    ps_info = load_ps_info([listener.pid for listener in listeners])
    launchd_map = load_launchd_pid_map()

    for listener in listeners:
        info = ps_info.get(listener.pid, {})
        listener.ppid = info.get("ppid")
        listener.cpu = info.get("cpu")
        listener.mem = info.get("mem")
        listener.etime = info.get("etime")
        listener.full_command = info.get("full_command")

        known = dict(KNOWN_SERVICES.get(listener.port, {}))
        command_text = " ".join(
            part for part in [listener.command, listener.full_command or ""] if part
        )
        for pattern, rule in COMMAND_RULES:
            if pattern.search(command_text):
                known.update(rule)

        label = known.get("launchd_label")
        if not label:
            label = launchd_map.get(listener.pid)
        if not label and listener.ppid is not None:
            label = launchd_map.get(listener.ppid)

        listener.launchd_label = label
        listener.category = known.get("category", listener.category)
        listener.name = known.get("name", listener.name)
        listener.reason = known.get("reason", listener.reason)
        listener.stop_policy = known.get("stop_policy", listener.stop_policy)

        if listener.port in PROTECTED_PORTS:
            listener.category = "protected"
            listener.stop_policy = "blocked"


def listener_to_dict(listener: Listener) -> dict[str, Any]:
    return {
        "port": listener.port,
        "protocol": listener.protocol,
        "pid": listener.pid,
        "ppid": listener.ppid,
        "user": listener.user,
        "command": listener.command,
        "full_command": listener.full_command,
        "cpu_percent": listener.cpu,
        "mem_percent": listener.mem,
        "elapsed": listener.etime,
        "addresses": sorted(listener.addresses),
        "launchd_label": listener.launchd_label,
        "category": listener.category,
        "name": listener.name,
        "reason": listener.reason,
        "stop_policy": listener.stop_policy,
    }


def print_report(listeners: list[Listener]) -> None:
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    unique_ports = sorted({listener.port for listener in listeners})
    print(f"Local Port Guard report generated_at={now}")
    print(f"unique_ports={len(unique_ports)} listener_rows={len(listeners)}")
    print("")
    print(
        "PORT   PID     CPU%  MEM%  CATEGORY         POLICY      LAUNCHD LABEL                         NAME"
    )
    print(
        "-----  ------  ----  ----  ---------------  ----------  ------------------------------------  ------------------------------"
    )
    for listener in listeners:
        cpu = "-" if listener.cpu is None else f"{listener.cpu:.1f}"
        mem = "-" if listener.mem is None else f"{listener.mem:.1f}"
        label = listener.launchd_label or "-"
        print(
            f"{listener.port:<5}  {listener.pid:<6}  {cpu:>4}  {mem:>4}  "
            f"{listener.category:<15}  {listener.stop_policy:<10}  {label[:36]:<36}  {listener.name}"
        )

    print("")
    for listener in listeners:
        print(f"[{listener.port}] {listener.name}")
        print(f"  category: {listener.category}")
        print(f"  policy: {listener.stop_policy}")
        print(f"  pid: {listener.pid} ppid: {listener.ppid or '-'} elapsed: {listener.etime or '-'}")
        print(f"  launchd: {listener.launchd_label or '-'}")
        print(f"  reason: {listener.reason}")
        print(f"  command: {listener.full_command or listener.command}")
        print("")


def find_listener_by_port(listeners: list[Listener], port: int) -> Listener | None:
    matches = [listener for listener in listeners if listener.port == port]
    if not matches:
        return None
    return matches[0]


def stop_plan(listener: Listener) -> list[list[str]]:
    uid = os.getuid()
    if listener.launchd_label:
        return [["launchctl", "bootout", f"gui/{uid}/{listener.launchd_label}"]]
    return [["kill", "-TERM", str(listener.pid)]]


def stop_port(port: int, execute: bool) -> int:
    listeners = scan_lsof()
    apply_metadata(listeners)
    listener = find_listener_by_port(listeners, port)
    if listener is None:
        print(f"port {port} is not listening")
        return 0

    print(f"target port: {port}")
    print(f"name: {listener.name}")
    print(f"category: {listener.category}")
    print(f"policy: {listener.stop_policy}")
    print(f"pid: {listener.pid}")
    print(f"launchd: {listener.launchd_label or '-'}")
    print(f"reason: {listener.reason}")

    if listener.stop_policy in {"blocked", "readonly"}:
        print("decision: refused")
        print("why: this listener is protected or system read-only by local policy")
        return 2

    commands = stop_plan(listener)
    print("plan:")
    for command in commands:
        print("  " + " ".join(command))

    if not execute:
        print("dry_run: true")
        print("rerun with --execute to apply this stop plan")
        return 0

    for command in commands:
        result = run_command(command)
        if result.returncode != 0:
            print(f"command_failed: {' '.join(command)}", file=sys.stderr)
            if result.stderr.strip():
                print(result.stderr.strip(), file=sys.stderr)
            return result.returncode

    verify = scan_lsof()
    remaining = [item for item in verify if item.port == port]
    if remaining:
        print("verification: failed")
        for item in remaining:
            print(f"still_listening pid={item.pid} command={item.command}")
        return 3

    print("verification: stopped")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan and safely manage local listening TCP ports.")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan listening ports and print a classified report.")
    scan_parser.add_argument("--json", action="store_true", help="Output JSON instead of text.")

    stop_parser = subparsers.add_parser("stop", help="Stop one explicitly selected non-protected port.")
    stop_parser.add_argument("--port", type=int, required=True, help="Listening TCP port to stop.")
    stop_parser.add_argument("--execute", action="store_true", help="Execute the stop plan. Omitted means dry-run.")

    args = parser.parse_args(argv)
    command = args.command or "scan"

    if command == "scan":
        listeners = scan_lsof()
        apply_metadata(listeners)
        if getattr(args, "json", False):
            print(json.dumps([listener_to_dict(item) for item in listeners], ensure_ascii=False, indent=2))
        else:
            print_report(listeners)
        return 0

    if command == "stop":
        return stop_port(args.port, args.execute)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
