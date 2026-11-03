#!/usr/bin/env python3
"""Loopback-only receiver for synthetic laboratory canary values."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


LOG_PATH = Path(os.environ.get("CANARY_LOG_PATH", "/var/log/lab-target/canary-received.jsonl"))
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
CANARY_RE = re.compile(r"^CANARY-[A-Za-z0-9_-]{8,120}$")
WRITE_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "LabCanaryReceiver/1.0"

    def _json(self, status: int, body: dict[str, object]) -> None:
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/collect":
            self._json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid_content_length"})
            return
        if length <= 0 or length > 4096:
            self._json(413, {"error": "invalid_body_size"})
            return

        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "invalid_json"})
            return

        run_id = payload.get("run_id") if isinstance(payload, dict) else None
        canary = payload.get("canary_value") if isinstance(payload, dict) else None
        source_ip = payload.get("source_ip", "unknown") if isinstance(payload, dict) else "unknown"
        if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
            self._json(400, {"error": "invalid_run_id"})
            return
        if not isinstance(canary, str) or not CANARY_RE.fullmatch(canary):
            self._json(400, {"error": "canary_must_be_synthetic_and_prefixed_CANARY"})
            return
        if not isinstance(source_ip, str) or len(source_ip) > 64:
            source_ip = "unknown"

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "canary_value": canary,
            "source_ip": source_ip,
        }
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
        with WRITE_LOCK, LOG_PATH.open("ab") as log_file:
            log_file.write(line)

        self._json(200, {"received": True, "run_id": run_id, "canary_value": canary})

    def log_message(self, fmt: str, *args: object) -> None:
        # Request bodies are never written to stdout/systemd logs.
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8080), Handler)
    server.serve_forever()
