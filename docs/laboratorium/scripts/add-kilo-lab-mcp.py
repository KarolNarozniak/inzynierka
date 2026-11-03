#!/usr/bin/env python3
"""Safely merge the local stdio and remote policy MCP servers into Kilo config."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path


CONFIG_PATH = Path.home() / ".config/kilo/kilo.jsonc"
SERVERS = {
    "lab-mcp-control": {
        "type": "remote",
        "url": "http://10.10.20.10:8001/mcp",
        "enabled": True,
        "timeout": 240_000,
    },
    "lab-mcp-local": {
        "type": "local",
        "command": [
            "/opt/lab/agent-mcp/venv/bin/python",
            "/opt/lab/agent-mcp/local_mcp_stdio.py",
        ],
        "enabled": True,
        "timeout": 10_000,
    },
}


def main() -> int:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existed = CONFIG_PATH.is_file()
    original_text = CONFIG_PATH.read_text(encoding="utf-8") if existed else "{}\n"
    original_mode = stat.S_IMODE(CONFIG_PATH.stat().st_mode) if existed else 0o600
    try:
        data = json.loads(original_text)
    except json.JSONDecodeError as error:
        raise SystemExit("Kilo config is not strict JSON; no changes were made.") from error
    if not isinstance(data, dict):
        raise SystemExit("Kilo config root must be an object; no changes were made.")

    mcp = data.setdefault("mcp", {})
    if not isinstance(mcp, dict):
        raise SystemExit("Existing top-level mcp setting is not an object; no changes were made.")

    additions: list[str] = []
    for name, wanted in SERVERS.items():
        existing = mcp.get(name)
        if existing is None:
            mcp[name] = wanted
            additions.append(name)
        elif existing != wanted:
            raise SystemExit(f"{name} exists with different settings; no changes were made.")

    if not additions:
        print("Both lab MCP server entries already match; no changes made.")
        return 0

    if existed:
        backup = CONFIG_PATH.with_name(
            f"{CONFIG_PATH.name}.bak-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        )
        shutil.copy2(CONFIG_PATH, backup)
        os.chmod(backup, 0o600)

    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, min(original_mode, 0o600))
    temporary_path.replace(CONFIG_PATH)
    os.chmod(CONFIG_PATH, min(original_mode, 0o600))

    print("lab_mcp_entries=" + ",".join(additions))
    print("config_permissions=" + oct(stat.S_IMODE(CONFIG_PATH.stat().st_mode)))
    print("Existing provider settings and secrets were not displayed or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
