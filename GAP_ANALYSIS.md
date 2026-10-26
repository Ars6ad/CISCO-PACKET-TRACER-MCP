# Industry-readiness gap analysis

Audited 2026-10-26 against the reference repository at commit
`1a4eae5e2f0bec97e85d4518b9f8cdf831468d6b`, Cisco Packet Tracer 9.0.0
installed locally, and comparable current MCP projects. The detailed evidence
is in `REFERENCE_FILE_AUDIT.md`. This file is a delivery contract: an item is
not complete until it has an automated test, user documentation, and—where
applicable—a live Packet Tracer integration test.

## Current verified state

PacketCraft has seven offline MCP tools plus an original Script Module mailbox
adapter. The adapter generates its own Script Engine source, validates a fixed
action vocabulary, records heartbeats, and accepts only correlated receipts.
It now has a small verified model/port/cable catalog and converts a reviewed
topology plan into deterministic typed create/link actions. Its IOS compiler
supports explicit static routes and OSPF, EIGRP, and RIP configuration output.
It has not yet completed a live end-to-end Packet Tracer test, so it is **not**
yet suitable for controlling a lab, grading a lab, or making a deployment claim.

The end-user release target is one `PacketCraft-Bridge.pts` file, mirroring the
reference project's distribution model. Portable source is present under
`extension/`; its encrypted `.pts` release artifact has not yet been exported
by Packet Tracer and therefore must not be represented as available.

## Required capabilities

| Area | Missing capability | Priority | Acceptance evidence |
|---|---|---:|---|
| Live connectivity | Native authenticated PTMP adapter for PT 9 | Experimental | A running PT instance is discovered, authenticated, queried, and cleanly disconnected |
| Live connectivity | Persistent Script Module mailbox bridge | P0 — source and protocol complete; installation/live test pending | Module heartbeat, a topology query, and a correlated receipt are observed |
| Safety | Approval gates, dry-run, idempotency keys, rollback/backup, audit log | P0 | Failed deploy leaves a recorded backup and no silent partial success |
| Topology | Device, port, module, cable, and versioned model catalogs | P0 | Unsupported models/ports are rejected before deploy |
| Topology | Live create/query/rename/move/delete device and link operations | P0 | Plan-to-live diff and reconciliation pass on PT |
| Configuration | IOS command execution, typed interface/IP/DHCP/static/OSPF/EIGRP/RIP support | P0 | Static/OSPF/EIGRP/RIP offline compilation exists; config read-back and end-to-end reachability still need to prove each protocol |
| Verification | Ping, traceroute, adjacency checks, routing-table checks, health checks | P0 | Post-deploy receipt reports measured, not assumed, state |
| Reliability | Timeouts, retry policy, cancellation, stale-result protection, concurrency limits | P0 | Fault-injection tests cover dropped and delayed replies |
| Security | Per-install secret storage, localhost bind, host validation, request/body limits, redact secrets | P0 | Threat-model and regression tests pass |
| Validation | Schema, graph, port/cable, IP/VLAN, routing, and service dependency validation | P1 | Invalid plans are rejected with actionable typed findings |
| Repair automation | Diagnose, propose repair, require approval, apply, verify, and record result | P1 | A broken lab is detected and repaired under a test fixture |
| Switching | VLANs, trunks, router-on-a-stick, STP, EtherChannel, port security | P1 | Each has compile and live verification coverage |
| Security services | ACLs, NAT/PAT, SSH/hardening, security audit and remediation | P1 | Policy intent matches running config and connectivity tests |
| Endpoints/services | PC/laptop/server configuration; DHCP, DNS, HTTP, FTP, email, firewall | P1 | Endpoint application and service tests pass |
| IPv6/wireless | SLAAC/DHCPv6, dual stack, AP/WLC/Wi-Fi validation | P1 | Dual-stack and association tests pass |
| Simulation | Simulation mode, controlled stepping, packet/event trace normalization | P2 | Packet trace is captured and correlated to a requested flow |
| Physical/activities | Physical workspace, power, modules, activity assessment/grading | P2 | Fixture reports physical state and score correctly |
| UX | Natural-language intent parser with explicit assumptions and reviewable plan | P2 | Ambiguous prompt returns questions, not guessed topology |
| UX | Resources, prompts, progress events, clear errors, client setup guides | P2 | Claude/Codex/VS Code smoke tests pass |
| Engineering | Versioned public schemas, API compatibility tests, lint/type/security scans, CI, release artifacts | P1 | Protected CI succeeds from a clean checkout |
| Observability | Structured logs, metrics, trace IDs, redaction, diagnostic bundle | P1 | One deployment is traceable end to end |
| Governance | License/SBOM, vulnerability policy, privacy policy, contribution guide | P2 | Release package includes all documents |

## Comparison with current projects

- The reference project provides planning, live deployment, a broad tool catalog, panel/service control, simulation, and bridge hardening. PacketCraft currently has only the offline planning core.
- `pktctl` demonstrates a stronger native PTMP approach: no polling extension, typed IPC arguments, physical workspace and activity coverage. PacketCraft needs the same native-adapter principle.
- `PacketTracer_mcp` demonstrates that Packet Tracer 9 ships a first-party Java IPC framework, but the JAR is proprietary and must be obtained from the user’s own Packet Tracer installation. PacketCraft will not redistribute it.
- Existing extension-based servers prove a Script Module bridge is practical but require careful loopback authentication and replay/stale-result defenses.

## Delivery order

1. Harden the offline core and freeze its schemas.
2. Add the adapter abstraction, secure job protocol, fake adapter, tests, and diagnostics.
3. Install and live-test the Script Module mailbox adapter on this machine's Packet Tracer; retain PTMP as an experimental alternative.
4. Add topology CRUD, catalog, config execution, deploy transaction, read-back verification, and repair automation.
5. Add switching/services/security/IPv6/wireless/simulation/physical features in tested vertical slices.

## Constraints

Packet Tracer is a simulator, not a production network controller. “Industry-qualified” here means reliable, secure, observable automation for Packet Tracer labs and teaching environments—not suitability for configuring production Cisco devices. Production-network support would require separate adapters built on supported Cisco APIs (for example NETCONF/RESTCONF) and separate safety controls.
