#!/usr/bin/env python3
"""One safe MCP read through the Agent-facing policy proxy for PCAP capture."""

from __future__ import annotations

import argparse
import json
import secrets
import urllib.error
import urllib.request
from datetime import UTC, datetime


DEFAULT_URL = "http://10.10.20.10:8001/mcp"
PROTOCOL_VERSION = "2024-11-05"


def post_message(url: str, payload: dict[str, object], headers: dict[str, str]) -> tuple[dict[str, object] | None, str | None]:
    request_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8", "replace")
        session_id = response.headers.get("Mcp-Session-Id")
        if not body.strip():
            return None, session_id

        if response.headers.get("Content-Type", "").startswith("text/event-stream"):
            data_lines = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
            if not data_lines:
                raise RuntimeError("MCP returned an empty event stream")
            body = data_lines[-1]

        message = json.loads(body)
        if not isinstance(message, dict):
            raise RuntimeError("MCP returned a non-object JSON response")
        return message, session_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--run-id",
        default=f"PCAP-MCP-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4)}",
    )
    args = parser.parse_args()

    headers: dict[str, str] = {}
    try:
        initialized, session_id = post_message(
            args.url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "lab-pcap-smoke", "version": "1.0.0"},
                },
            },
            headers,
        )
        if not initialized or "error" in initialized:
            raise RuntimeError("MCP initialize failed")

        negotiated_version = initialized.get("result", {}).get("protocolVersion", PROTOCOL_VERSION)
        headers["MCP-Protocol-Version"] = str(negotiated_version)
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        post_message(
            args.url,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers,
        )
        result, _ = post_message(
            args.url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "read_untrusted_note",
                    "arguments": {"run_id": args.run_id},
                },
            },
            headers,
        )
        if not result or "error" in result or result.get("result", {}).get("isError"):
            raise RuntimeError("read_untrusted_note failed through policy proxy")

    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"mcp_pcap_smoke=FAILED reason={type(exc).__name__}: {exc}")
        return 1

    print("mcp_initialize=OK")
    print("tool=read_untrusted_note result=OK")
    print(f"run_id={args.run_id}")
    print("canary_submitted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
