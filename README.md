# PacketCraft MCP

> A safety-first MCP server for designing, validating, compiling, and gradually
> automating Cisco Packet Tracer labs.

PacketCraft is an original Python implementation built around typed topology
plans and explicit deployment actions. It uses the public
[`Mats2208/MCP-Packet-Tracer`](https://github.com/Mats2208/MCP-Packet-Tracer)
project only as a clean-room capability benchmark; no source code, packaged
extension, or proprietary Packet Tracer dependency has been copied.

## Project status

**Early development / not production-ready.** PacketCraft has a tested offline
planning core and a safer foundation for live automation. It is not yet a
complete replacement for the reference project, and it has not passed an
end-to-end Packet Tracer live-deployment smoke test.

| Area | Status | What is available today |
|---|---|---|
| Typed topology plans | Available | Validated Pydantic/JSON schema for devices, links, addresses, routing, and static routes |
| IPv4 planning | Available | Deterministic `/24` LAN and `/30` router-transit allocation |
| IOS configuration generation | Available | Router hostname/interface configuration plus static routes, OSPF, EIGRP, and RIP output |
| Device and cable catalog | Initial | Tested Packet Tracer 9 model, port, and cable facts for common routers, switches, hosts, servers, and APs |
| MCP server | Available | Stdio MCP tools for planning, compilation, persistence, deployment preview, and adapters |
| Script Module transport | Source complete | Typed mailbox bridge source, heartbeat diagnostics, job receipts, and offline-deploy protection |
| Live Packet Tracer deployment | **Not verified** | Action vocabulary exists, but a packaged extension and real Packet Tracer smoke test are still required |
| Native PTMP transport | Experimental | Narrow Java sidecar protocol; not the recommended automation route |

## Why PacketCraft

Packet Tracer automation should be reviewable and safe. PacketCraft therefore
uses declarative plans and a fixed action protocol rather than sending arbitrary
JavaScript to Packet Tracer.

- **Typed by default** — plans, routes, devices, cables, and actions are
  validated before Packet Tracer is touched.
- **Preview before mutation** — deployment actions can be compiled and reviewed
  before an explicit approval is supplied.
- **No raw code execution** — the Script Module accepts a small allowlist of
  JSON actions; it never uses `eval` or `new Function` on job contents.
- **Receipts, not assumptions** — queued work is not called successful until
  the Script Module writes a correlated receipt.
- **Portable source** — the extension derives its mailbox location from the
  current Packet Tracer user folder; no developer-specific path is embedded.

## Architecture

```text
MCP client
    │
    ▼
Typed topology plan ──► validation ──► allocation / IOS compiler
    │                                      │
    └────────────────────► deployment preview ──► explicit approval
                                                    │
                                                    ▼
                                      Packet Tracer adapter
                                      ├─ Script Module mailbox (primary)
                                      ├─ authenticated loopback bridge (future webview path)
                                      └─ PTMP Java sidecar (experimental)
                                                    │
                                                    ▼
                                         correlated receipt / diagnostics
```

The detailed design is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

- Python **3.11+**
- Cisco Packet Tracer **9** only for live-adapter work
- Java/JDK only when building the optional experimental PTMP sidecar

The offline planning and compiler features do **not** require Packet Tracer to
be installed.

## Install and run

Clone the repository, create an isolated environment, and install the package
with test dependencies:

```powershell
git clone https://github.com/Ars6ad/CISCO-PACKET-TRACER-MCP.git
Set-Location CISCO-PACKET-TRACER-MCP

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[test]
```

Run the offline verification suite:

```powershell
python -m pytest -q
```

Start the MCP server over standard input/output:

```powershell
packetcraft-mcp
```

For an MCP client configuration, point its command at the virtual
environment’s `packetcraft-mcp` executable. Do not add logging to standard
output: stdio is reserved for MCP messages.

## What the MCP server can do

### Offline planning and artifacts

| Tool | Purpose |
|---|---|
| `pc_validate` | Validate graph structure, addresses, routing prerequisites, and static-route requirements |
| `pc_allocate_ipv4` | Deterministically allocate IPv4 addresses for a topology |
| `pc_compile_ios` | Generate router IOS configuration text from assigned addresses and routing intent |
| `pc_summarize` | Return topology device/link/component facts |
| `pc_deployment_manifest` | Produce a checksummed deployment manifest |
| `pc_save_plan` / `pc_load_plan` | Atomically save and load plan JSON |
| `pc_list_device_models` | List the currently verified Packet Tracer device/port catalog |
| `pc_deployment_preview` | Resolve a plan into deterministic typed create/link actions without modifying Packet Tracer |

### Script Module adapter

| Tool | Purpose |
|---|---|
| `pc_script_module_prepare` | Generate the portable Script Module source for the local user |
| `pc_script_module_status` | Read module heartbeat and mailbox diagnostics |
| `pc_script_module_queue` | Queue a validated, typed action batch |
| `pc_script_module_job_status` | Read a correlated job receipt; absence of a receipt is not success |
| `pc_deploy_to_script_module` | Queue a reviewed plan only with `approve: true` and an active module heartbeat |

### Other adapters

| Tool group | Status |
|---|---|
| `pc_bridge_*` | Optional authenticated loopback bridge foundation; not the primary deployment route |
| `pc_ptmp_*` | Experimental Cisco Packet Tracer IPC/PTMP sidecar support; use only for evaluation |

The full tool signatures are in [src/packetcraft_mcp/server.py](src/packetcraft_mcp/server.py).

## Topology-plan example

The MCP tools accept JSON text. This minimal example creates two routers and
two hosts, assigns OSPF, and leaves interface selection to the catalog:

```json
{
  "name": "two-site-lab",
  "devices": [
    {"name": "R1", "kind": "router", "model": "2911", "x": 100, "y": 100},
    {"name": "R2", "kind": "router", "model": "2911", "x": 450, "y": 100},
    {"name": "PC1", "kind": "host", "model": "PC-PT", "x": 100, "y": 280},
    {"name": "PC2", "kind": "host", "model": "PC-PT", "x": 450, "y": 280}
  ],
  "links": [
    {"a": "R1", "b": "R2"},
    {"a": "R1", "b": "PC1"},
    {"a": "R2", "b": "PC2"}
  ],
  "routing": {"protocol": "ospf", "ospf_process": 1}
}
```

Recommended workflow:

1. Call `pc_validate`.
2. Call `pc_allocate_ipv4` and validate the returned plan again.
3. Call `pc_compile_ios` to inspect generated router configuration.
4. Call `pc_deployment_preview` and review the exact device/link actions.
5. Only after the Script Module heartbeat is healthy, call
   `pc_deploy_to_script_module` with `approve: true`.
6. Poll `pc_script_module_job_status` and treat only a `succeeded` receipt as
   an execution result.

## Live Packet Tracer setup

The intended end-user experience is one `PacketCraft-Bridge.pts` extension
installed through **Extensions → Scripting → Configure PT Script Modules →
Add**.

That encrypted `.pts` release artifact is **not published yet**. Cisco Packet
Tracer owns the format and does not document a command-line packager, so this
repository deliberately does not fake one or redistribute another project’s
extension.

Until a release package exists, a maintainer must export it from the portable
[extension source](extension/packetcraft-bridge.js) in Packet Tracer’s Script
Module editor. Configure the module for **On Startup**—not On Demand—and grant
only the documented minimum privileges: Get Network, Change Network, Misc GUI,
Change GUI, and File.

Follow [SCRIPT_MODULE_SETUP.md](SCRIPT_MODULE_SETUP.md) before attempting any
live deployment. The extension’s current typed action allowlist is:

```text
ping, query_topology, create_device, delete_device, rename_device,
move_device, connect_ports, disconnect_port
```

## Security model

- Script Module jobs are JSON files written atomically to
  `%USERPROFILE%\PacketCraft\script-bridge`.
- Every job has an opaque ID and every result is stored as a correlated receipt.
- The module emits a short-lived heartbeat. `pc_deploy_to_script_module` refuses
  to queue live changes while that heartbeat is absent.
- The optional HTTP bridge binds to loopback, validates the `Host` header,
  limits body size, and uses a per-install bearer token.
- PacketCraft intentionally exposes no `send_raw`, arbitrary JavaScript, or
  arbitrary shell-command MCP tool.
- PTMP secrets and Packet Tracer’s proprietary Java framework stay outside the
  repository; local ignore rules prevent accidental publication.

## Not done yet

This list is deliberately explicit. Do not use PacketCraft to claim these
features are available.

### Required before reliable live automation

- Export, package, and independently smoke-test `PacketCraft-Bridge.pts`.
- Run a real Packet Tracer end-to-end test: heartbeat → topology query → create
  device/link → receipt → post-condition read-back.
- Add deployment transactions with idempotency, timeout/retry/cancellation,
  reconciliation/diff, backup/rollback, audit records, and measured health
  verification.
- Implement a robust CLI session layer with prompt detection, command
  timeouts, configuration read-back, and tests.

### Network functionality not implemented

- VLANs, trunks, router-on-a-stick, STP, EtherChannel, port security, and QoS.
- ACLs, NAT/PAT, SSH hardening, security audit, and remediation.
- DHCP, DNS, HTTP, FTP, email, host firewalls, and Server-PT services.
- IPv6, DHCPv6/SLAAC, wireless AP/WLC workflows, and association validation.
- Hardware modules, physical workspace, device power, and activity/grading
  support.
- Simulation mode, stepping, and normalized packet-trace collection.
- Device-panel automation, desktop applications, screenshots, and web browser
  controls.
- Natural-language intent planning, templates, auto-fix/repair workflows, MCP
  resources/prompts, CI, release automation, SBOM, and contribution policy.

See [PARITY.md](PARITY.md) for the capability ledger and
[GAP_ANALYSIS.md](GAP_ANALYSIS.md) for priorities and acceptance criteria.

## Reference comparison

The clean-room file-by-file audit records the current reference project’s
architecture, all 79 observed MCP tools, and each independently implemented or
missing PacketCraft capability:

- [REFERENCE_FILE_AUDIT.md](REFERENCE_FILE_AUDIT.md) — authoritative audit and
  roadmap.
- [REFERENCE_AUDIT.md](REFERENCE_AUDIT.md) — earlier audit summary.
- [PARITY.md](PARITY.md) — concise capability status.

The reference is more feature-complete today. PacketCraft’s goal is not to
imitate its implementation, but to independently reach and exceed its useful
capabilities with stronger typed boundaries and verifiable live behavior.

## Development

Refresh the generated portable Script Module source after changing
`script_bridge.py`:

```powershell
python -m packetcraft_mcp.export_extension_source
node --check extension\packetcraft-bridge.js
python -m pytest -q
```

The test suite is intentionally designed to run without Packet Tracer. A future
separate integration suite must verify all claims that involve a live Packet
Tracer instance.

## Scope and disclaimer

PacketCraft automates a network simulator for labs, learning, and repeatable
demonstrations. It is **not** a production Cisco network-management system.
Production-device automation requires separate supported adapters (such as
NETCONF, RESTCONF, or a carefully controlled SSH integration), credentials
handling, change management, and operational safeguards.
