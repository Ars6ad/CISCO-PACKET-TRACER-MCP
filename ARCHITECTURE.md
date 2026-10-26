# PacketCraft live-automation architecture

PacketCraft uses a port-and-adapter design so no planner or validation rule depends on a particular Packet Tracer transport.

```
MCP client → typed plan → validation → deployment transaction → PT adapter
                                            │                   ├─ Script Module file mailbox (primary)
                                            │                   └─ PTMP native sidecar (experimental)
                                            └→ receipt + read-back verification + audit log
```

## Non-negotiable safety rules

- A live mutation has a transaction ID, idempotency key, timeout, structured receipt, and post-condition.
- A deploy starts with a preview and optional backup. It is never reported successful without a Packet Tracer acknowledgement and read-back verification.
- Secrets are generated per installation and stored outside the project with least-privilege file permissions; they are redacted from every tool result and log.
- The fallback bridge binds only to loopback, validates `Host`, caps request sizes, authenticates every mutation, and rejects stale or replayed results.
- An arbitrary JavaScript execution endpoint is not part of the standard MCP surface.

## Primary Script Module adapter

Packet Tracer's persistent Script Engine can use the documented in-process `ipc`
API to operate the active logical workspace. PacketCraft writes validated typed
JSON jobs to a local mailbox; the module writes a heartbeat and a correlated
receipt per job. No job contains JavaScript, and the module does not use `eval`.
The extension must run **On Startup**: Packet Tracer's **On Demand** mode only
starts for a saved-data, web-view, or inter-module-message trigger, not for a
file arriving in an external mailbox. See `SCRIPT_MODULE_SETUP.md`.

## Native PTMP adapter (experimental)

Packet Tracer 9 includes Cisco's Java IPC framework in its local installation. The sidecar will compile against the user-provided JAR during setup, authenticate with user-created application credentials, and expose a narrow JSON-lines local protocol to the Python server. The proprietary JAR and credentials are ignored by Git and never packaged.

## Loopback HTTP bridge

The existing authenticated loopback bridge remains an optional future web-view
transport. The file-mailbox Script Module is preferred because it continues to
run when no custom web view is open.
