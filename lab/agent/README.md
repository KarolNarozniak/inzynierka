# Local MCP for VM-Agent

This server is a fixed-fixture, stdio-only MCP component for the local/remote transport comparison.
It exposes `read_local_note`, `read_indirect_instruction`, and `read_protected_canary`; none accepts
an arbitrary path. The indirect fixture contains synthetic test instructions. The protected-canary
tool reads one root-owned file whose group ACL defines the context comparison. The server writes
event metadata, not fixture contents or canary values, to the caller's
`~/.local/state/lab-agent/local-mcp.jsonl` and does not open a network listener.

## Deployment target

- Install the pinned `mcp==1.30.0` environment under `/opt/lab/agent-mcp/venv` on VM-Agent.
- Run the server using Kilo's local MCP configuration (`type: local`) and absolute command/args.
- `docs/laboratorium/scripts/add-kilo-lab-mcp.py` merges both lab MCP entries into the current
  user's `~/.config/kilo/kilo.jsonc`, preserves unrelated settings, and creates a mode-0600 backup.
- Configure separate per-user Kilo profiles for the unprivileged `agent-wide` and `agent-limited`
  accounts; do not copy API credentials or VS Code secret storage between accounts.
- Neither account belongs to `sudo`, `lxd`, or other privileged groups. `agent-wide` alone belongs
  to `lab-canary-readers`; the protected test file is root-owned, mode `0640`, and contains only a
  per-run synthetic canary. `agent-limited` cannot traverse its directory/read the file.
- This comparison tests a narrow OS file-permission context, not full VM or container isolation.
- Fluent Bit tails the per-user MCP JSONL event file; auditd watches the server, interpreter, fixtures,
  protected-canary file and profile configuration. The note text and canary value are not written to
  the MCP event log.

## Verification

Run `verify_local_mcp.py` from the pinned environment. It starts the server as a child over stdio,
initializes MCP, invokes the fixed note once, and prints a synthetic run ID. Confirm matching local
JSONL and auditd events. For the H2 comparison, prepare one canary with
`sudo /opt/lab/agent-mcp/venv/bin/python /opt/lab/agent-mcp/prepare_protected_canary.py RUN_ID`,
then invoke `read_protected_canary` from both Kilo identities with the same run ID. `agent-wide`
should read it; `agent-limited` should receive a permission-denied MCP result. The helper records
only the value hash, never the canary itself. No PCAP connection to a local stdio server is expected.

## Privilege-context pair

The recovery/admin account `vmagent` is not used as either experimental Kilo identity. Create two
unprivileged accounts with `setup-context-users.sh`; `agent-wide` is the only account added to the
`lab-canary-readers` group, while `agent-limited` is not. Neither belongs to `sudo`, `lxd`, or other
privileged groups. The controlled comparison is narrowly the OS permission to read the synthetic
protected fixture; it does not claim VM or container isolation.

`install-kilo-extension-for-context-users.sh` copies only the installed extension code, not the
`vmagent` VS Code profile or credential store. Set desktop login passwords and configure the
LiteLLM client credential separately in each user's Kilo UI; do not put it in this repository or
an experiment manifest.
