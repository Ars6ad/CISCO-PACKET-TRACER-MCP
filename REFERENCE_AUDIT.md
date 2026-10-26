# Clean-room audit of `Mats2208/MCP-Packet-Tracer`

Superseded by the complete [REFERENCE_FILE_AUDIT.md](REFERENCE_FILE_AUDIT.md),
which was refreshed on 2026-10-26 against public commit
`1a4eae5e2f0bec97e85d4518b9f8cdf831468d6b`. This earlier note remains as a
historical architecture summary. PacketCraft does not include the reference
implementation, its extension assets, or its PTBuilder-derived files.

## What the reference does differently

Its live control path is extension-first:

1. A Packet Tracer Script Module is the in-application controller.
2. A file mailbox lets the Script Engine continue working while no web-view panel is open.
3. A web-view can also long-poll a localhost HTTP service for lower-latency panel work.
4. Jobs carry correlation IDs; results are retained by ID rather than consumed from one global FIFO.
5. A local persisted secret protects the HTTP channel, because loopback plus CORS alone does not stop a browser from sending a request.

The reference also has a much wider MCP surface (planning, topology, configuration, services, security, switching, simulation, UI panels, and deployment workflows). That breadth does not itself prove live reliability; each capability still needs a Packet Tracer acceptance test.

## PacketCraft implementation decision

PacketCraft now uses the most important reliable part of that architecture, rebuilt independently from Cisco's installed Script Module documentation:

- primary transport: persistent Script Engine **file mailbox**;
- job format: typed JSON, one opaque job ID per file;
- execution: fixed action dispatch only — no raw JavaScript, `eval`, or `new Function`;
- replies: correlated JSON receipts plus a heartbeat;
- optional future transport: the pre-existing token-authenticated loopback HTTP bridge;
- retained alternative: PTMP native sidecar, currently experimental because this PT installation rejected logical-workspace mutation privileges.

This choice removes the dependency on an open control panel and avoids copying the reference project's extension build chain, which expects components it deliberately does not distribute.

## Parity status after this audit

| Capability | Reference approach | PacketCraft status |
|---|---|---|
| Persistent PT execution channel | Script Engine file bridge | Implemented; needs installation and live test |
| HTTP panel channel | web-view long poll + token | Existing optional bridge; no PacketCraft web-view yet |
| Typed topology actions | extension dispatch | Implemented for query/device/link CRUD |
| Raw code injection prevention | protocol guardrails | Implemented; regression-tested |
| Correlated job result | request ID/result store | Implemented per mailbox file |
| CLI configuration | extension helper stack | Not implemented; intentionally blocked pending terminal-session design |
| Service/switching/security/simulation tools | broad MCP catalog | Not yet implemented |

The next acceptance check is deliberately small: import the generated module, observe its heartbeat, queue `query_topology`, and compare the returned device count to Packet Tracer. Only then should create/delete/link mutations be enabled in a test topology.

## Release packaging

The reference provides a prebuilt `.pts` binary from its releases; PacketCraft
will do the same. The source in `extension/packetcraft-bridge.js` is portable
and is regression-tested to exactly match the generated local copy. The missing
release deliverable is `PacketCraft-Bridge.pts`, which must be exported once
through Packet Tracer because Cisco's `.pts` format is encrypted and has no
documented headless authoring API.
