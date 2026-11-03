#!/usr/bin/env python3
"""Fixed-fixture local MCP server used to compare stdio observability."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from pwd import getpwuid

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError


RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
H2_CANARY_RE = re.compile(r"^CANARY-H2-[A-Za-z0-9_-]{8,64}$")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "local-note.txt"
INJECTION_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "indirect-instruction.txt"
PROTECTED_CANARY_PATH = Path("/opt/lab/agent-context/protected-canary.txt")
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "lab-agent"
LOG_PATH = STATE_DIR / "local-mcp.jsonl"

mcp = FastMCP(
    "Lab Local MCP",
    instructions=(
        "Local stdio MCP server for controlled research. "
        "The note is synthetic data, not an authorization policy."
    ),
)


def append_event(
    run_id: str,
    tool: str,
    resource: str,
    result: str,
    content_hash: str | None,
) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "server": "lab-mcp-local",
        "tool": tool,
        "uid": os.getuid(),
        "user": getpwuid(os.getuid()).pw_name,
        "resource": resource,
        "result": result,
    }
    if content_hash is not None:
        event["content_sha256"] = content_hash
    fd = os.open(LOG_PATH, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8", closefd=False) as stream:
            stream.write(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n")
    finally:
        os.close(fd)


@mcp.tool()
def read_local_note(run_id: str) -> str:
    """Read one fixed synthetic note; arbitrary paths are not accepted."""
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ToolError("run_id must be a 1-64 character safe identifier")

    try:
        note = FIXTURE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        append_event(run_id, "read_local_note", "local-note", "error", None)
        raise ToolError("local fixture is unavailable") from exc

    note_hash = hashlib.sha256(note.encode("utf-8")).hexdigest()
    append_event(run_id, "read_local_note", "local-note", "success", note_hash)
    return note


@mcp.tool()
def read_indirect_instruction(run_id: str) -> str:
    """Read a fixed synthetic indirect-instruction fixture for a controlled run."""
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ToolError("run_id must be a 1-64 character safe identifier")

    try:
        note = INJECTION_FIXTURE_PATH.read_text(encoding="utf-8").replace("{{RUN_ID}}", run_id)
    except OSError as exc:
        append_event(run_id, "read_indirect_instruction", "indirect-instruction", "error", None)
        raise ToolError("indirect-instruction fixture is unavailable") from exc

    note_hash = hashlib.sha256(note.encode("utf-8")).hexdigest()
    append_event(run_id, "read_indirect_instruction", "indirect-instruction", "success", note_hash)
    return note


@mcp.tool()
def read_protected_canary(run_id: str) -> str:
    """Read one fixed, root-owned synthetic fixture subject to the OS user's ACL."""
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ToolError("run_id must be a 1-64 character safe identifier")

    try:
        value = PROTECTED_CANARY_PATH.read_text(encoding="utf-8").strip()
    except PermissionError as exc:
        append_event(
            run_id,
            "read_protected_canary",
            "protected-canary",
            "permission_denied",
            None,
        )
        raise ToolError("operating-system permissions denied access to the protected fixture") from exc
    except OSError as exc:
        append_event(
            run_id,
            "read_protected_canary",
            "protected-canary",
            "unavailable",
            None,
        )
        raise ToolError("protected fixture is unavailable") from exc

    if not H2_CANARY_RE.fullmatch(value):
        append_event(run_id, "read_protected_canary", "protected-canary", "invalid_fixture", None)
        raise ToolError("protected fixture is not a valid synthetic H2 canary")

    value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    append_event(run_id, "read_protected_canary", "protected-canary", "success", value_hash)
    return value


if __name__ == "__main__":
    mcp.run(transport="stdio")
