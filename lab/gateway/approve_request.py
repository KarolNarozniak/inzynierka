#!/usr/bin/env python3
"""Record a human decision for one pending `ask` MCP request on VM-Gateway."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path


REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
PENDING_DIR = Path("/var/lib/lab-control/pending")
APPROVAL_DIR = Path("/var/lib/lab-control/approvals")


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[2] not in {"allow", "deny"}:
        print("Usage: lab-control-approve REQUEST_ID allow|deny", file=sys.stderr)
        return 2

    request_id, decision = sys.argv[1], sys.argv[2]
    if not REQUEST_ID_RE.fullmatch(request_id):
        print("Invalid request ID", file=sys.stderr)
        return 2

    pending = PENDING_DIR / f"{request_id}.json"
    if not pending.is_file():
        print("No pending approval exists for this request ID", file=sys.stderr)
        return 1

    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "request_id": request_id,
        "decision": decision,
        "approved_by": os.environ.get("SUDO_USER") or os.environ.get("USER", "operator"),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    destination = APPROVAL_DIR / f"{request_id}.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=APPROVAL_DIR, delete=False
    ) as temporary:
        json.dump(payload, temporary)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(destination)
    print(f"Recorded {decision} for request {request_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
