#!/usr/bin/env python3
"""
Local Port Guard GUI

Small localhost web UI for outputs/local_port_guard.py.
It is intentionally local-only and keeps stop actions behind an explicit
confirmation endpoint. Protected ports remain blocked by the CLI guard.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
CLI = ROOT / "local_port_guard.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


INDEX_HTML = r"""<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Local Port Guard</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #0f1419;
        --panel: #161d24;
        --panel-2: #1d2630;
        --line: #2a3542;
        --text: #e7edf4;
        --muted: #9caaba;
        --accent: #6bb6ff;
        --danger: #ff6b6b;
        --warn: #f0b84f;
        --ok: #45c48a;
        --lock: #d8b653;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: var(--bg);
        color: var(--text);
        letter-spacing: 0;
      }
      button, input, select {
        font: inherit;
      }
      .app {
        min-height: 100vh;
        display: grid;
        grid-template-columns: 220px minmax(520px, 1fr) 380px;
      }
      aside, main, section {
        min-width: 0;
      }
      aside {
        border-right: 1px solid var(--line);
        padding: 16px;
        background: #111820;
      }
      .brand {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 16px;
      }
      .metric {
        display: grid;
        gap: 4px;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        margin-bottom: 10px;
        background: var(--panel);
      }
      .metric span {
        color: var(--muted);
        font-size: 12px;
      }
      .metric strong {
        font-size: 24px;
      }
      .filters {
        display: grid;
        gap: 8px;
        margin-top: 16px;
      }
      .filter {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        min-height: 36px;
        padding: 8px 10px;
        color: var(--text);
        background: transparent;
        border: 1px solid var(--line);
        border-radius: 8px;
        cursor: pointer;
      }
      .filter.active {
        border-color: var(--accent);
        background: #173149;
      }
      main {
        display: grid;
        grid-template-rows: auto 1fr;
        min-height: 100vh;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 16px;
        border-bottom: 1px solid var(--line);
        background: var(--panel);
      }
      .toolbar input {
        width: 320px;
        max-width: 50vw;
        padding: 8px 10px;
        color: var(--text);
        background: #0f151c;
        border: 1px solid var(--line);
        border-radius: 8px;
      }
      .toolbar button, .action {
        min-height: 34px;
        padding: 7px 12px;
        color: var(--text);
        background: var(--panel-2);
        border: 1px solid var(--line);
        border-radius: 8px;
        cursor: pointer;
      }
      .toolbar button:hover, .action:hover {
        border-color: var(--accent);
      }
      .table-wrap {
        overflow: auto;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
      }
      th, td {
        padding: 10px 12px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: middle;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      th {
        position: sticky;
        top: 0;
        background: #121a22;
        color: var(--muted);
        font-size: 12px;
        z-index: 1;
      }
      tr {
        cursor: pointer;
      }
      tr:hover, tr.selected {
        background: #182330;
      }
      .port {
        font-weight: 700;
      }
      .chip {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        min-height: 24px;
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid var(--line);
        font-size: 12px;
      }
      .protected { color: var(--lock); border-color: #6f5f2c; background: #2a2414; }
      .development { color: var(--accent); border-color: #255275; background: #11283b; }
      .signing { color: var(--warn); border-color: #685126; background: #281f10; }
      .system { color: var(--muted); border-color: #46505b; background: #18202a; }
      .browser-tooling, .mobile-dev { color: #bba7ff; border-color: #51437d; background: #211b34; }
      .unknown { color: #ff9f9f; border-color: #683838; background: #2b1818; }
      .detail {
        border-left: 1px solid var(--line);
        background: #111820;
        padding: 16px;
        overflow: auto;
      }
      .detail h2 {
        margin: 0 0 6px;
        font-size: 20px;
      }
      .detail .sub {
        color: var(--muted);
        margin-bottom: 14px;
      }
      .field {
        padding: 10px 0;
        border-bottom: 1px solid var(--line);
      }
      .field label {
        display: block;
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 4px;
      }
      .field code {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        color: #dfe8f2;
      }
      .stop {
        width: 100%;
        margin-top: 16px;
        color: #fff;
        background: #582325;
        border-color: #874044;
      }
      .stop:disabled {
        color: var(--muted);
        background: #202833;
        border-color: var(--line);
        cursor: not-allowed;
      }
      .status {
        margin-left: auto;
        color: var(--muted);
        font-size: 12px;
      }
      .notice {
        margin-top: 12px;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        color: var(--muted);
        line-height: 1.45;
      }
      @media (max-width: 980px) {
        .app {
          grid-template-columns: 1fr;
        }
        aside, .detail {
          border: 0;
          border-bottom: 1px solid var(--line);
        }
        main {
          min-height: auto;
        }
        .toolbar {
          flex-wrap: wrap;
        }
        .toolbar input {
          width: 100%;
          max-width: none;
        }
      }
    </style>
  </head>
  <body>
    <div class="app">
      <aside>
        <div class="brand">Local Port Guard</div>
        <div class="metric"><span>監聽 ports</span><strong id="portCount">-</strong></div>
        <div class="metric"><span>保護 ports</span><strong id="protectedCount">-</strong></div>
        <div class="filters" id="filters"></div>
      </aside>
      <main>
        <div class="toolbar">
          <input id="search" placeholder="搜尋 port、程序、分類、launchd label" />
          <button id="refresh">重新掃描</button>
          <span class="status" id="status">尚未掃描</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width:80px">Port</th>
                <th style="width:150px">分類</th>
                <th style="width:110px">Policy</th>
                <th style="width:90px">PID</th>
                <th style="width:170px">程序</th>
                <th>Launchd / 說明</th>
              </tr>
            </thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
      </main>
      <section class="detail" id="detail">
        <h2>尚未選取</h2>
        <div class="sub">點選左側任一 port 查看細節。</div>
      </section>
    </div>
    <script>
      const state = {
        items: [],
        selectedKey: null,
        filter: "all",
        search: ""
      };

      const categoryLabels = {
        all: "全部",
        protected: "保護",
        development: "開發",
        signing: "簽章",
        "browser-tooling": "瀏覽器工具",
        "mobile-dev": "行動開發",
        system: "系統",
        unknown: "未知"
      };

      function keyOf(item) {
        return `${item.port}:${item.pid}`;
      }

      function esc(value) {
        return String(value ?? "").replace(/[&<>"']/g, ch => ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;"
        })[ch]);
      }

      function matches(item) {
        const filterOk = state.filter === "all" || item.category === state.filter;
        const text = [
          item.port,
          item.pid,
          item.command,
          item.full_command,
          item.category,
          item.name,
          item.launchd_label,
          item.reason
        ].join(" ").toLowerCase();
        return filterOk && text.includes(state.search.toLowerCase());
      }

      function renderFilters() {
        const counts = new Map();
        counts.set("all", state.items.length);
        state.items.forEach(item => counts.set(item.category, (counts.get(item.category) || 0) + 1));
        const order = ["all", "protected", "development", "signing", "browser-tooling", "mobile-dev", "system", "unknown"];
        document.getElementById("filters").innerHTML = order.map(category => `
          <button class="filter ${state.filter === category ? "active" : ""}" data-filter="${category}">
            <span>${categoryLabels[category] || category}</span>
            <strong>${counts.get(category) || 0}</strong>
          </button>
        `).join("");
        document.querySelectorAll(".filter").forEach(button => {
          button.addEventListener("click", () => {
            state.filter = button.dataset.filter;
            render();
          });
        });
      }

      function renderRows() {
        const visible = state.items.filter(matches);
        document.getElementById("rows").innerHTML = visible.map(item => {
          const selected = keyOf(item) === state.selectedKey ? "selected" : "";
          const label = item.launchd_label || item.reason || "-";
          return `
            <tr class="${selected}" data-key="${esc(keyOf(item))}">
              <td class="port">${esc(item.port)}</td>
              <td><span class="chip ${esc(item.category)}">${esc(categoryLabels[item.category] || item.category)}</span></td>
              <td>${esc(item.stop_policy)}</td>
              <td>${esc(item.pid)}</td>
              <td>${esc(item.command)}</td>
              <td>${esc(label)}</td>
            </tr>
          `;
        }).join("");
        document.querySelectorAll("tbody tr").forEach(row => {
          row.addEventListener("click", () => {
            state.selectedKey = row.dataset.key;
            render();
          });
        });
      }

      function selectedItem() {
        return state.items.find(item => keyOf(item) === state.selectedKey) || state.items[0] || null;
      }

      function renderDetail() {
        const item = selectedItem();
        const detail = document.getElementById("detail");
        if (!item) {
          detail.innerHTML = `<h2>沒有資料</h2><div class="sub">目前沒有掃到任何 listening TCP port。</div>`;
          return;
        }
        state.selectedKey = keyOf(item);
        const canStop = item.stop_policy === "confirm";
        const lockedText = item.stop_policy === "blocked"
          ? "此 port 是保護項目，GUI 不提供停止入口。"
          : item.stop_policy === "readonly"
            ? "此項目依規則只讀顯示，不提供停止入口。"
            : item.stop_policy === "report-only"
              ? "未知項目只報告，不直接停止。"
              : "可停止，但需要明確確認。";
        detail.innerHTML = `
          <h2>${esc(item.port)} ${esc(item.name)}</h2>
          <div class="sub"><span class="chip ${esc(item.category)}">${esc(categoryLabels[item.category] || item.category)}</span></div>
          <div class="field"><label>處理策略</label><code>${esc(item.stop_policy)} - ${esc(lockedText)}</code></div>
          <div class="field"><label>PID / PPID / 存活時間</label><code>${esc(item.pid)} / ${esc(item.ppid || "-")} / ${esc(item.elapsed || "-")}</code></div>
          <div class="field"><label>CPU / Memory</label><code>${esc(item.cpu_percent ?? "-")} / ${esc(item.mem_percent ?? "-")}</code></div>
          <div class="field"><label>Launchd Label</label><code>${esc(item.launchd_label || "-")}</code></div>
          <div class="field"><label>原因</label><code>${esc(item.reason)}</code></div>
          <div class="field"><label>Command</label><code>${esc(item.full_command || item.command)}</code></div>
          <div class="field"><label>Addresses</label><code>${esc((item.addresses || []).join("\n"))}</code></div>
          <button class="action stop" id="stopBtn" ${canStop ? "" : "disabled"}>停止此 port</button>
          <div class="notice">停止流程會先呼叫後端產生 dry-run 計畫，確認後才執行。若此 port 由 launchd 管理，會優先停 launchd job。</div>
        `;
        const stopBtn = document.getElementById("stopBtn");
        if (stopBtn && canStop) {
          stopBtn.addEventListener("click", () => stopItem(item));
        }
      }

      function render() {
        document.getElementById("portCount").textContent = new Set(state.items.map(item => item.port)).size;
        document.getElementById("protectedCount").textContent = state.items.filter(item => item.category === "protected").length;
        renderFilters();
        renderRows();
        renderDetail();
      }

      async function refresh() {
        document.getElementById("status").textContent = "掃描中";
        const res = await fetch("/api/scan");
        if (!res.ok) {
          document.getElementById("status").textContent = `掃描失敗 ${res.status}`;
          return;
        }
        state.items = await res.json();
        if (!state.items.find(item => keyOf(item) === state.selectedKey)) {
          state.selectedKey = state.items[0] ? keyOf(state.items[0]) : null;
        }
        document.getElementById("status").textContent = `已更新 ${new Date().toLocaleTimeString()}`;
        render();
      }

      async function stopItem(item) {
        const planRes = await fetch(`/api/stop?port=${encodeURIComponent(item.port)}`);
        const planText = await planRes.text();
        if (!planRes.ok && planRes.status !== 409) {
          alert(planText);
          return;
        }
        const ok = confirm(`停止 port ${item.port}？\n\n${planText}`);
        if (!ok) return;
        const execRes = await fetch(`/api/stop?port=${encodeURIComponent(item.port)}&execute=1`, { method: "POST" });
        const execText = await execRes.text();
        alert(execText);
        await refresh();
      }

      document.getElementById("refresh").addEventListener("click", refresh);
      document.getElementById("search").addEventListener("input", event => {
        state.search = event.target.value;
        render();
      });
      refresh();
    </script>
  </body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalPortGuard/0.1"

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html", "/api/scan"}:
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.respond(200, INDEX_HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/scan":
            self.api_scan()
            return
        if parsed.path == "/api/stop":
            self.api_stop(parsed.query, execute_allowed=False)
            return
        self.respond(404, "not found\n", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/stop":
            self.api_stop(parsed.query, execute_allowed=True)
            return
        self.respond(404, "not found\n", "text/plain; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def respond(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def api_scan(self) -> None:
        result = self.run_cli(["scan", "--json"])
        if result.returncode != 0:
            body = result.stderr or result.stdout or "scan failed\n"
            self.respond(500, body, "text/plain; charset=utf-8")
            return
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError:
            self.respond(500, "scan returned invalid json\n", "text/plain; charset=utf-8")
            return
        self.respond(200, result.stdout, "application/json; charset=utf-8")

    def api_stop(self, query: str, execute_allowed: bool) -> None:
        params = parse_qs(query)
        port_values = params.get("port") or []
        if not port_values:
            self.respond(400, "missing port\n", "text/plain; charset=utf-8")
            return
        try:
            port = int(port_values[0])
        except ValueError:
            self.respond(400, "invalid port\n", "text/plain; charset=utf-8")
            return

        execute = execute_allowed and params.get("execute") == ["1"]
        args = ["stop", "--port", str(port)]
        if execute:
            args.append("--execute")
        result = self.run_cli(args)
        status = 200 if result.returncode == 0 else 409
        body = result.stdout or result.stderr or f"stop returned {result.returncode}\n"
        self.respond(status, body, "text/plain; charset=utf-8")


def main(argv: list[str]) -> int:
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    if len(argv) >= 1:
        port = int(argv[0])
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Local Port Guard GUI listening on http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
