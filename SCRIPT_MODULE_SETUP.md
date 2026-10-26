# Packet Tracer Script Module bridge

This is the primary live-automation route for Packet Tracer 9 on this machine. It uses Packet Tracer's built-in Script Engine and its documented `ipc` API, not PTMP.

## One-time installation

For an end user, install the published `PacketCraft-Bridge.pts` with **Extensions
→ Scripting → Configure PT Script Modules → Add**. That is the intended one-file
experience.

Until the first PacketCraft `.pts` release is exported, a publisher must make it
once from `extension/packetcraft-bridge.js` as documented in
`extension/README.md`. The Script Module must use **On Startup**; `On Demand`
will not wake merely because an MCP job file appears. It needs only **Get
Network**, **Change Network**, **Misc GUI**, **Change GUI**, and **File**.

The first export is the only manual packaging step. Packet Tracer owns the
encrypted `.pts` format and does not document a command-line packager. Do not
download an untrusted `.pts`; compile the checked-in source in your own Packet
Tracer installation, then distribute that one resulting extension file.

After installation, restart Packet Tracer (or start the module in the Script
Engine UI), then call `pc_script_module_status`. It must report
`script_module_alive: true` before queuing any mutation.

## What it executes today

The extension accepts only typed mailbox actions: `ping`, `query_topology`, `create_device`, `delete_device`, `rename_device`, `move_device`, `connect_ports`, and `disconnect_port`. It does not accept raw JavaScript or shell commands.

`run_cli` is intentionally not enabled yet: it needs a separate command-session implementation with prompt detection, timeout handling, read-back, and tests. A job’s receipt is the source of truth; do not assume success until `pc_script_module_job_status` says `succeeded`.

## Safety model

The mailbox is stored under the current user's PacketCraft home folder
(`%USERPROFILE%\\PacketCraft\\script-bridge`). Jobs use atomic writes, opaque
IDs, a heartbeat, and per-job receipts. The generated Script Module is
self-contained ES5 code and dispatches a fixed action vocabulary; it never
calls `eval` or executes content from a job file as source code.
