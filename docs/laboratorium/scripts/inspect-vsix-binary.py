#!/usr/bin/env python3
"""Extract and report embedded Kilo CLI binaries from a VSIX archive."""

import sys
import zipfile
from pathlib import Path


archive = Path(sys.argv[1])
output = Path(sys.argv[2])
with zipfile.ZipFile(archive) as vsix:
    candidates = [name for name in vsix.namelist() if name.endswith("/bin/kilo")]
    if not candidates:
        raise SystemExit("No bin/kilo member found in VSIX")
    for name in candidates:
        data = vsix.read(name)
        output.write_bytes(data)
        print(f"member={name} bytes={len(data)} magic={data[:4].hex()}")
