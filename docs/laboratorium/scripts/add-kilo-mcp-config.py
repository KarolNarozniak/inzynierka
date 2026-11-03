#!/usr/bin/env python3
"""Safely merge the lab MCP policy proxy into Kilo's global JSON config."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path


CONFIG_PATH = Path.home() / ".config/kilo/kilo.jsonc"
SERVER_NAME = "lab-mcp-control"
SERVER_CONFIG = {
    "type": "remote",
    "url": "http://10.10.20.10:8001/mcp",
    "enabled": True,
    # The secured policy can wait for an operator's manual `ask` decision.
    "timeout": 240_000,
}


def main() -> int:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"Kilo config not found: {CONFIG_PATH}")

    original_mode = stat.S_IMODE(CONFIG_PATH.stat().st_mode)
    original_text = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        data = json.loads(original_text)
    except json.JSONDecodeError as error:
        raise SystemExit(
            "Kilo config is not strict JSON. No changes were made; inspect JSONC comments/trailing commas first."
        ) from error
    if not isinstance(data, dict):
        raise SystemExit("Kilo config root must be an object; no changes were made.")

    mcp_config = data.setdefault("mcp", {})
    if not isinstance(mcp_config, dict):
        raise SystemExit("Existing top-level mcp setting is not an object; no changes were made.")
    existing = mcp_config.get(SERVER_NAME)
    if existing is not None:
        if existing == SERVER_CONFIG:
            print("lab-mcp-control already has the requested endpoint; no changes made.")
            return 0
        raise SystemExit("lab-mcp-control already exists with different settings; no changes were made.")

    backup = CONFIG_PATH.with_name(
        f"{CONFIG_PATH.name}.bak-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    shutil.copy2(CONFIG_PATH, backup)
    os.chmod(backup, 0o600)

    mcp_config[SERVER_NAME] = SERVER_CONFIG
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(CONFIG_PATH)
    os.chmod(CONFIG_PATH, 0o600)

    print(f"Added {SERVER_NAME}: {SERVER_CONFIG['url']}")
    print(f"Backup: {backup.name} (mode 600)")
    print(f"Config permissions: {oct(stat.S_IMODE(CONFIG_PATH.stat().st_mode))}")
    print("Existing provider settings and secrets were preserved and not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
