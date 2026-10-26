# Reference file audit and clean-room parity ledger

**Reference:** `Mats2208/MCP-Packet-Tracer` at commit
`1a4eae5e2f0bec97e85d4518b9f8cdf831468d6b` (pulled 2026-10-26).

This is a clean-room analysis of public behavior and architecture. It does not
copy reference source, extension assets, PTBuilder files, or release binaries.
“Parity” below means independently implemented behavior with PacketCraft tests,
not matching names or source lines.

## Audit method and scope

The pinned repository was freshly cloned and its complete tracked tree indexed:

- 79 registered MCP tools, extracted from decorators and checked against the
  repository's own generated `CODEMAP.md`;
- Python application code organised into adapter, application, domain,
  infrastructure, shared, and developer-tool layers;
- its three extension files (`script-engine/core.js`, `script-engine/main.js`,
  and webview `interface.js`) plus HTML shell;
- all regression-test file names and their assertions as the observable
  behavior contract;
- packaging, security, installation, documentation, and skill files.

Binary demo media is not reverse engineered because it carries no executable
behavior. Generated cache and Git metadata are also out of scope.

## Architecture recovered from the files

```text
MCP server entry point
  ├─ MCP adapters: 79 tool wrappers, resources, prompts, panel support
  ├─ application use cases: plan/build/validate/export and feature application
  ├─ domain: Pydantic data, deterministic rules, planning/audit/diff services
  └─ infrastructure
       ├─ catalogs (device/port/cable/module/template facts)
       ├─ generators (typed IOS commands and Packet Tracer API payloads)
       ├─ execution (HTTP bridge, file mailbox, console driver, deployments)
       ├─ persistence (plans/projects)
       └─ Windows UI presenter (optional)

Packet Tracer extension
  ├─ Script Engine: persistent file mailbox and Packet Tracer IPC helpers
  └─ webview: authenticated localhost HTTP long-poll and operator panel
```

The reference explicitly has two live channels: a Script Engine file mailbox
that works while its panel is closed, and an HTTP webview channel for interactive
operations. Its extension executes JavaScript requests through a dynamic-code
helper. PacketCraft must **not** reproduce that raw-code exposure; its
independent bridge will keep a typed action protocol.

## File groups and responsibilities

| Reference paths | Recovered responsibility | PacketCraft state |
|---|---|---|
| `server.py`, `settings.py`, `__main__.py`, `skill_install.py` | Server lifecycle, instructions, HTTP/stdio, workdir and skill distribution | Partial |
| `adapters/mcp/{tool_registry,resource_registry,prompt_registry}.py` | Registry-driven MCP surface, catalogs/resources and prompts | Missing |
| `adapters/mcp/bridge_context.py` | Chooses HTTP versus file transport, tracks live connection and correlated replies | Partial: only file mailbox path exists |
| `adapters/mcp/tools/*.py` | 62 topic-specific wrappers around use cases and live operations | Mostly missing |
| `adapters/mcp/{device_panel_tools,desktop_service_tools,panel_support}.py` | Router/host/Server-PT panels, CLI session and optional window presentation | Missing |
| `application/dto/*.py` | Boundary request/response objects | Missing |
| `application/use_cases/*.py` | Orchestrates validation, generators and deployment for each feature | Partial only for basic planning |
| `domain/models/*.py` | Plan, routing, ACL, NAT, VLAN, service and hardening models | Basic topology model only |
| `domain/rules/*.py` | Static and live-topology validation rules | Basic graph/IP validation only |
| `domain/services/*.py` | Planner, address allocator, estimates, repair, diff, audit and packet-trace summaries | Basic allocation/summary plus plan-to-action compiler |
| `infrastructure/catalog/*.py` | Model aliases, ports, cable rules, module compatibility and templates | Partial: initial PT 9 model/port/cable facts |
| `infrastructure/generator/*.py` | IOS configuration and Packet Tracer API payload generation | Original static/OSPF/EIGRP/RIP offline IOS compiler; no live CLI engine |
| `infrastructure/execution/*.py` | Secure bridge, mailbox, deployment/reconciliation and console engine | File mailbox plus approval-gated action queue; no reconciliation/console engine |
| `infrastructure/persistence/*.py` | Managed project-plan storage | Basic JSON save/load |
| `infrastructure/ui/*.py` | Optional Windows device-window UI automation and screenshots | Missing |
| `EXTENSION/script-engine/{core,main}.js` | PT IPC helpers, module startup, persistent mailbox and helper installation | Clean-room typed mailbox prototype |
| `EXTENSION/webview/{index,interface}.js` | Operator panel and authenticated HTTP long-poll | Missing by design until core live path passes |
| `tests/*.py` | Behavior/security/regression contract across all components | 26 PacketCraft offline/security tests; no live parity suite yet |

## Exact reference MCP tool inventory

The list below is factual inventory, not a promise that every feature is already
safe or supported by Packet Tracer 9. The “PacketCraft” column is the current
clean-room status.

| Area | Reference tools | PacketCraft status |
|---|---|---|
| Planning and projects | `pt_list_devices`, `pt_list_templates`, `pt_get_device_details`, `pt_estimate_plan`, `pt_plan_topology`, `pt_validate_plan`, `pt_fix_plan`, `pt_explain_plan`, `pt_generate_script`, `pt_generate_configs`, `pt_export`, `pt_deploy`, `pt_list_projects`, `pt_load_project` | Basic validate/address/static-OSPF-EIGRP-RIP generation/save-load only |
| Live lifecycle | `pt_full_build`, `pt_live_deploy`, `pt_bridge_status`, `pt_verify_connectivity`, `pt_save_project`, `pt_open_project` | Script mailbox heartbeat/job status only |
| Topology | `pt_query_topology`, `pt_export_topology`, `pt_delete_device`, `pt_rename_device`, `pt_move_device`, `pt_delete_link`, `pt_add_device`, `pt_add_link`, `pt_set_port`, `pt_send_raw` | Typed query/device/link actions pending first live test; intentionally no raw-code tool |
| Modules | `pt_list_modules`, `pt_add_module`, `pt_install_modules_batch`, `pt_remove_module` | Missing |
| Inspection | `pt_diff`, `pt_health_check`, `pt_inspect_ports`, `pt_device_power` | Missing |
| ACL and NAT | `pt_apply_acl`, `pt_apply_acl_object`, `pt_remove_acl_object`, `pt_remove_acl`, `pt_apply_nat`, `pt_remove_nat` | Missing |
| Switching and hardening | `pt_apply_vlan`, `pt_apply_stp`, `pt_apply_port_security`, `pt_apply_hardening`, `pt_apply_interface_tuning`, `pt_read_vlans` | Missing |
| Network services | `pt_apply_netflow`, `pt_configure_dhcp_server`, `pt_read_qos` | Missing |
| Security and canvas | `pt_audit_security`, `pt_screenshot`, `pt_add_note`, `pt_clear_annotations` | Missing |
| Simulation | `pt_simulation_mode`, `pt_simulation_step`, `pt_read_packet_trace` | Missing |
| Project controls | `pt_backup_config`, `pt_project_metadata`, `pt_workspace_options` | Missing |
| Device panels | `pt_ui_mode`, `pt_cli`, `pt_host_command`, `pt_ui_open`, `pt_ui_close`, `pt_ui_capture`, `pt_host_ip_config`, `pt_read_device_panel` | Missing |
| Desktop and Server-PT | `pt_web_browser`, `pt_server_dhcp`, `pt_server_dns`, `pt_server_http`, `pt_server_service`, `pt_email_client`, `pt_host_firewall`, `pt_terminal` | Missing |

## Detailed implementation order

The reference files indicate these dependencies; building tool wrappers before
their data catalog and deployment invariants would create a large but unreliable
surface.

1. **Releaseable extension + live smoke test.** Export one portable `.pts`,
   verify the mailbox heartbeat, then query a real empty topology.
2. **Catalog and topology read model.** Device/port/cable/module facts; query,
   create, rename, move, link and delete with post-condition checks.
3. **Deployment transaction.** Preview/diff, idempotency, per-action receipts,
   reconciliation, timeouts, backup/audit record and rollback strategy.
4. **Plan compiler.** Templates, IPv4/IPv6, DHCP, static/OSPF/EIGRP/RIP,
   deterministic layout and generated configs.
5. **Verification and repair.** Real ping, link/port health, topology diff and
   approval-gated diagnose/propose/apply/verify repair.
6. **Feature vertical slices.** VLAN/STP/port security; ACL/NAT/hardening;
   Server-PT services; modules; simulation; panels/UI.
7. **Product quality.** Resources/prompts, versioned schemas, CI, packaging,
   changelog, SBOM/license policy and a test fixture for every live claim.

## Explicit non-parity decisions

- No `pt_send_raw` equivalent: accepting arbitrary JavaScript would defeat the
  typed-job safety boundary and permit unintended Packet Tracer actions.
- No claim that a `.pts` exists until Packet Tracer exports and smoke-tests it.
- No claim that a Packet Tracer simulator controller is production Cisco network
  automation. Production devices need a separate NETCONF/RESTCONF/SSH adapter.

## Current audit conclusion

PacketCraft is at the beginning of parity, not the end: it has a tested offline
core (including explicit static, OSPF, EIGRP, and RIP configuration generation)
and a safer initial Script Module protocol. The reference has substantially more
implemented capability. This ledger is the governing source checklist for the
clean-room rebuild; a row changes to implemented only with PacketCraft source,
unit tests, documentation, and a relevant live acceptance test.
