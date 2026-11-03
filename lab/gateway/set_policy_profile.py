#!/usr/bin/env python3
"""Select a named laboratory tool-policy profile atomically."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path


POLICY_PATH = Path("/opt/lab/control/policy.json")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: lab-control-set-profile PROFILE", file=sys.stderr)
        return 2
    profile = sys.argv[1]
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if profile not in data.get("profiles", {}):
        print(f"Unknown profile: {profile}", file=sys.stderr)
        print("Available: " + ", ".join(sorted(data.get("profiles", {}))), file=sys.stderr)
        return 2
    previous_profile = data.get("active_profile", "unknown")
    original_stat = POLICY_PATH.stat()
    data["active_profile"] = profile
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=POLICY_PATH.parent, delete=False
    ) as temporary:
        json.dump(data, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.chown(temporary_path, original_stat.st_uid, original_stat.st_gid)
    os.chmod(temporary_path, stat.S_IMODE(original_stat.st_mode))
    temporary_path.replace(POLICY_PATH)
    audit_path = Path("/var/log/lab-control/decisions.jsonl")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": "control-plane",
        "request_id": str(uuid.uuid4()),
        "stage": "policy_profile_change",
        "previous_profile": previous_profile,
        "active_profile": profile,
        "operator": os.environ.get("SUDO_USER") or os.environ.get("USER", "vmgateway"),
        "source": "lab-control-set-profile",
    }
    with audit_path.open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(event, separators=(",", ":")) + "\n")
    os.chmod(audit_path, 0o600)
    print(f"Active lab MCP policy profile: {profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
