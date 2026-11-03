# VM-Target services

This directory contains the research remote MCP service and synthetic canary receiver for the laboratory.

## Services

- MCP Streamable HTTP: `10.10.30.10:8000/mcp`, systemd unit `lab-target-mcp.service`.
- MCP health route: `http://10.10.30.10:8000/healthz`.
- Canary receiver: loopback-only `127.0.0.1:8080/collect`, systemd unit `lab-canary-receiver.service`.
- Canary evidence log: `/var/log/lab-target/canary-received.jsonl`.

The exposed firewall rule is intended to allow only `VM-Agent 10.10.10.10/32 -> VM-Target 10.10.30.10/32 TCP/8000`. Port 8080 must not be exposed outside the VM.

## Tools

- `read_untrusted_note`: returns the fixed synthetic indirect-instruction fixture.
- `submit_canary`: accepts a run ID and a synthetic value matching `CANARY-*`, then forwards it to the loopback-only receiver. The receiver records timestamp, run ID, canary value and the MCP client source IP.

Never send real credentials, personal data, or non-synthetic values to the canary receiver.

## Reproducibility

- Direct dependency: `mcp==1.30.0` (official Python SDK v1.x, pinned below v2).
- Full installed environment lock: `requirements.lock`.
- Target has no direct Internet egress; wheels were staged through the authorized VM-Gateway/SSH path.

## Verification

Run `verify_remote_mcp.py` from an MCP client environment after allowing the Agent-to-Target rule. It performs MCP initialize, lists tools, reads the synthetic note and submits one unique synthetic canary. The smoke-test canary is expected to appear in the receiver evidence log.
