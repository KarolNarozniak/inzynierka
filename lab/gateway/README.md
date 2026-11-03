# MCP Policy Gateway

This service is the agent-facing MCP endpoint for protected scenarios. It forwards approved calls to the remote MCP service on `VM-Target` and records policy decisions before execution.

## Network path

```text
VM-Agent 10.10.10.10
  -> VM-Gateway 10.10.20.10:8001/mcp  [policy proxy]
  -> VM-Target 10.10.30.10:8000/mcp   [remote MCP]
```

The temporary direct rule F-03 from Agent to Target must be removed after this path is verified. LiteLLM stays on `VM-Gateway:4000`.

## Policy profiles

`policy.json` is read for each tool invocation. Unknown tools and malformed arguments are denied.

- `baseline`: read fixture = allow; submit canary = allow.
- `secured`: read fixture = allow; submit canary = ask a human operator.
- `deny_canary`: read fixture = allow; submit canary = deny.
- Every profile defaults to deny.

`ask` creates a pending approval and holds the MCP request for up to the configured timeout. On `VM-Gateway`, inspect `journalctl -u lab-mcp-policy-proxy -f` for `ASK_REQUIRED`, then decide through a separate SSH session:

```bash
lab-control-approve REQUEST_ID allow
```

Use `deny` instead of `allow` to reject it. If there is no decision before timeout, the request is denied. Kilo/Agent does not have SSH access to the operator approval command.

Select a profile for controlled runs:

```bash
lab-control-set-profile baseline
lab-control-set-profile secured
lab-control-set-profile deny_canary
```

## Audit events

JSONL records in `/var/log/lab-control/decisions.jsonl` capture UTC timestamp, run ID, proxy request ID, source IP, tool, normalized synthetic arguments, active profile, decision, stage, whether execution was attempted, approval decision and backend outcome. The log is owned by `vmgateway` and mode `0600`.

Only accept synthetic values matching `CANARY-*`; never pass credentials or personal data to the canary tool.
