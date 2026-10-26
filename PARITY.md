# Capability parity ledger

Reference audited: `Mats2208/MCP-Packet-Tracer` at
`1a4eae5e2f0bec97e85d4518b9f8cdf831468d6b` (2026-10-26). The complete
file-by-file clean-room audit is in [REFERENCE_FILE_AUDIT.md](REFERENCE_FILE_AUDIT.md).
This is a requirements ledger, not copied source code.

| Capability area | Reference | PacketCraft status | Acceptance condition |
|---|---:|---|---|
| Device/module/cable catalog | Yes | Partial | Initial PT 9 device/port/cable catalog with tests; modules pending |
| Natural-language planning | Yes | Planned | Intent parser produces typed plans |
| Typed topology plan | Yes | Complete | Pydantic model and stable JSON contract |
| Automatic IPv4 allocation | Yes | Complete | Deterministic LAN /24 and transit /30 allocation |
| Static / OSPF / EIGRP / RIP configs | Yes | Partial | Explicit static routes plus OSPF/EIGRP/RIP compiler; live configuration/read-back still required |
| VLAN/trunk/inter-VLAN/STP/port-security | Yes | Planned | Compiler plus live verification |
| ACL/NAT/hardening | Yes | Planned | Idempotent compiler and audit |
| DHCP/router and Server-PT services | Yes | Planned | Address plan to service configuration |
| IPv6 and wireless | Yes | Planned | Dual-stack and wireless validation |
| Plan validation/auto-fix | Yes | Partial | Structural and IP-conflict validation; repair next |
| Script and CLI generation/export | Yes | Partial | IOS config export and portable PT extension source; CLI-session automation and a signed/exported `.pts` remain |
| Project persistence | Yes | Complete | Atomic JSON save/load |
| Live topology CRUD/inspection | Yes | Partial | Typed device/link action protocol, reviewed deployment compiler, and offline-module refusal; live test pending |
| Live deploy/reconcile/diff/health | Yes | Planned | Transaction receipts and post-deploy diff |
| Packet simulation/tracing | Yes | Planned | Extension adapter + normalized traces |
| Device panel/desktop apps/UI capture | Yes | Planned | Optional Windows adapter |
| Backup/project metadata/workspace options | Yes | Planned | Extension adapter |
| Secure HTTP + file bridge | Yes | Partial | Typed file mailbox and optional authenticated HTTP bridge; HTTP/webview channel pending |
| MCP resources/prompts | Yes | Partial | Tools available; resources/prompts next |

## Improvements required for “better”

1. A deploy command is transactional: validate → preview manifest → apply → acknowledgement → verify → receipt.
2. Each generated artifact records inputs, compiler version, and checksums for reproducibility.
3. No general-purpose `send_raw` tool is exposed by default; privileged escape hatches must be explicitly enabled.
4. The test suite must run without Packet Tracer, while a separate integration suite verifies the extension.
