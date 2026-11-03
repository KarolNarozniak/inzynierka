#!/usr/bin/env python3
"""Add a least-tool Kilo permission profile for the controlled lab accounts."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path


CONFIG_PATH = Path.home() / ".config/kilo/kilo.jsonc"
LAB_PERMISSIONS = {
    "*": "deny",
    "lab-mcp-local_read_local_note": "allow",
    "lab-mcp-local_read_indirect_instruction": "allow",
    "lab-mcp-local_read_protected_canary": "allow",
    "lab-mcp-control_read_untrusted_note": "allow",
    # The client may send only this lab tool call to the proxy. The Gateway policy
    # remains the authoritative allow/ask/deny decision point for submit_canary.
    "lab-mcp-control_submit_canary": "allow",
}


def main() -> int:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"Kilo config not found: {CONFIG_PATH}; add lab MCP servers first.")
    original_text = CONFIG_PATH.read_text(encoding="utf-8")
    original_mode = stat.S_IMODE(CONFIG_PATH.stat().st_mode)
    try:
        data = json.loads(original_text)
    except json.JSONDecodeError as error:
        raise SystemExit("Kilo config is not strict JSON; no changes were made.") from error
    if not isinstance(data, dict):
        raise SystemExit("Kilo config root must be an object; no changes were made.")

    existing = data.get("permission")
    if existing is not None and existing != LAB_PERMISSIONS:
        raise SystemExit("Existing permission settings differ; inspect manually, no changes made.")
    if existing == LAB_PERMISSIONS:
        print("Lab experiment permissions already match; no changes made.")
        return 0

    backup = CONFIG_PATH.with_name(
        f"{CONFIG_PATH.name}.bak-permissions-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    shutil.copy2(CONFIG_PATH, backup)
    os.chmod(backup, 0o600)
    data["permission"] = LAB_PERMISSIONS

    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, min(original_mode, 0o600))
    temporary_path.replace(CONFIG_PATH)
    os.chmod(CONFIG_PATH, min(original_mode, 0o600))
    print("lab_tool_allowlist=local MCP fixtures and policy-proxy MCP only")
    print("built_in_read_edit_shell_and_other_tools=deny")
    print("Existing provider settings and secrets were not displayed or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
