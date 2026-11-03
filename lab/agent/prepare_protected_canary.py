#!/usr/bin/env python3
"""Create one unique root-owned synthetic canary for the context comparison."""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import re
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path


RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
GROUP_NAME = "lab-canary-readers"
CANARY_DIR = Path("/opt/lab/agent-context")
CANARY_PATH = CANARY_DIR / "protected-canary.txt"
METADATA_DIR = Path("/var/lib/lab-agent-context")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="unique synthetic experiment run ID")
    args = parser.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("Run this helper with sudo; it writes only synthetic data and metadata.")
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise SystemExit("run_id must contain 1-64 safe identifier characters")

    try:
        readers_gid = grp.getgrnam(GROUP_NAME).gr_gid
    except KeyError as exc:
        raise SystemExit(f"Required group does not exist: {GROUP_NAME}") from exc

    CANARY_DIR.mkdir(parents=True, exist_ok=True)
    os.chown(CANARY_DIR, 0, 0)
    os.chmod(CANARY_DIR, 0o755)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    os.chown(METADATA_DIR, 0, 0)
    os.chmod(METADATA_DIR, 0o700)

    value = "CANARY-H2-" + secrets.token_hex(12)
    data = (value + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=CANARY_DIR, delete=False) as temporary:
        temporary.write(data)
        temp_path = Path(temporary.name)
    os.chown(temp_path, 0, readers_gid)
    os.chmod(temp_path, 0o640)
    temp_path.replace(CANARY_PATH)
    os.chown(CANARY_PATH, 0, readers_gid)
    os.chmod(CANARY_PATH, 0o640)

    metadata = {
        "run_id": args.run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "resource": str(CANARY_PATH),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "owner": "root",
        "reader_group": GROUP_NAME,
        "mode": "0640",
        "canary_value": "<not recorded>",
    }
    metadata_path = METADATA_DIR / f"{args.run_id}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    os.chown(metadata_path, 0, 0)
    os.chmod(metadata_path, 0o600)

    print(f"run_id={args.run_id}")
    print(f"resource={CANARY_PATH}")
    print(f"sha256={metadata['sha256']}")
    print(f"size_bytes={len(data)}")
    print("canary_value=<not displayed>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
