from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .bridge import BridgeServer
from .catalog import list_models
from .core import allocate_ipv4, artifact_manifest, compile_ios, graph_summary, load_plan, save_plan, validate
from .deployment import deployment_preview
from .models import TopologyPlan
from .ptmp import NativePtmpClient, load_settings, prepare_pairing, refresh_registration
from .script_bridge import ScriptMailbox, ScriptBridgeError

mcp = FastMCP("PacketCraft MCP", instructions="Design and validate Packet Tracer topology plans before deployment. All results are JSON.")
bridge_server = BridgeServer()
script_mailbox = ScriptMailbox.default()


def _plan(plan_json: str) -> TopologyPlan:
    return TopologyPlan.model_validate_json(plan_json)


@mcp.tool()
def pc_validate(plan_json: str) -> str:
    """Validate a typed PacketCraft topology plan without Packet Tracer."""
    return validate(_plan(plan_json)).model_dump_json(indent=2)


@mcp.tool()
def pc_allocate_ipv4(plan_json: str, lan_pool: str = "10.10.0.0/16") -> str:
    """Allocate deterministic IPv4 addresses for a plan."""
    return allocate_ipv4(_plan(plan_json), lan_pool).model_dump_json(indent=2)


@mcp.tool()
def pc_compile_ios(plan_json: str) -> str:
    """Compile router IOS configurations. The plan must have assigned addresses."""
    return json.dumps(compile_ios(_plan(plan_json)), indent=2)


@mcp.tool()
def pc_summarize(plan_json: str) -> str:
    """Return connectivity and size facts for a plan."""
    return json.dumps(graph_summary(_plan(plan_json)), indent=2)


@mcp.tool()
def pc_deployment_manifest(plan_json: str) -> str:
    """Create a checksummed manifest for a future live deployment transaction."""
    return json.dumps(artifact_manifest(_plan(plan_json)), indent=2)


@mcp.tool()
def pc_save_plan(plan_json: str, directory: str = "projects") -> str:
    """Atomically persist a plan as JSON."""
    return json.dumps({"path": str(save_plan(_plan(plan_json), directory))})


@mcp.tool()
def pc_load_plan(path: str) -> str:
    """Load a previously saved PacketCraft plan."""
    return load_plan(path).model_dump_json(indent=2)


@mcp.tool()
def pc_bridge_start(port: int = 0) -> str:
    """Start the authenticated loopback bridge for the optional PT Script Module."""
    if port < 0 or port > 65535:
        raise ValueError("port must be from 0 to 65535")
    return json.dumps({"address": bridge_server.start(port), "pairing_secret": bridge_server.bridge.token})


@mcp.tool()
def pc_bridge_status() -> str:
    """Return non-sensitive bridge state. It does not assert Packet Tracer is connected."""
    return json.dumps({"running": bridge_server.running, "address": bridge_server.address, "jobs": bridge_server.bridge.summary()})


@mcp.tool()
def pc_queue_actions(actions_json: str) -> str:
    """Queue a typed action batch for a paired Packet Tracer adapter; raw JavaScript is forbidden."""
    actions = json.loads(actions_json)
    if not isinstance(actions, list):
        raise ValueError("actions_json must be a JSON array")
    job = bridge_server.bridge.enqueue(actions)
    return json.dumps({"job_id": job.id, "state": job.state})


@mcp.tool()
def pc_job_status(job_id: str) -> str:
    """Read a queued action job and its explicit receipt, if any."""
    from dataclasses import asdict
    return json.dumps(asdict(bridge_server.bridge.status(job_id)))


@mcp.tool()
def pc_script_module_prepare() -> str:
    """Generate the Packet Tracer Script Module source for this Windows user."""
    return json.dumps({"script_path": str(script_mailbox.prepare()), "setup_guide": "SCRIPT_MODULE_SETUP.md"})


@mcp.tool()
def pc_script_module_status() -> str:
    """Report whether the installed Packet Tracer Script Module is alive."""
    return json.dumps(script_mailbox.diagnostics())


@mcp.tool()
def pc_script_module_queue(actions_json: str) -> str:
    """Queue validated typed Packet Tracer actions for the installed Script Module."""
    try:
        actions = json.loads(actions_json)
        job_id = script_mailbox.queue(actions)
    except (json.JSONDecodeError, ScriptBridgeError) as error:
        raise ValueError(str(error)) from error
    return json.dumps({"job_id": job_id, "state": "pending"})


@mcp.tool()
def pc_script_module_job_status(job_id: str) -> str:
    """Read the explicit receipt for a Script Module job; no receipt means no success claim."""
    try:
        return json.dumps(script_mailbox.status(job_id))
    except ScriptBridgeError as error:
        raise ValueError(str(error)) from error


@mcp.tool()
def pc_list_device_models() -> str:
    """List PacketCraft's verified Packet Tracer 9 models and physical ports."""
    return json.dumps({"schema": "packetcraft/device-catalog/v1", "models": list_models()}, indent=2)


@mcp.tool()
def pc_deployment_preview(plan_json: str) -> str:
    """Resolve a plan into explicit typed live actions without changing Packet Tracer."""
    return json.dumps(deployment_preview(_plan(plan_json)), indent=2)


@mcp.tool()
def pc_deploy_to_script_module(plan_json: str, approve: bool = False) -> str:
    """Queue a reviewed plan for live PT execution only when approve is explicitly true."""
    preview = deployment_preview(_plan(plan_json))
    if not approve:
        return json.dumps({"queued": False, "reason": "explicit approval required", "preview": preview}, indent=2)
    diagnostics = script_mailbox.diagnostics()
    if not diagnostics["script_module_alive"]:
        return json.dumps({
            "queued": False,
            "reason": "Packet Tracer Script Module is not alive; open its .pts extension and enable On Startup before deployment",
            "script_module": diagnostics,
            "preview": preview,
        }, indent=2)
    job_id = script_mailbox.queue(preview["actions"])
    return json.dumps({"queued": True, "job_id": job_id, "state": "pending", "action_count": len(preview["actions"])})


@mcp.tool()
def pc_ptmp_prepare(application_id: str = "io.packetcraft.mcp") -> str:
    """Create a local PTMP registration file and secret. You must add the file in Packet Tracer's IPC UI yourself."""
    return json.dumps(prepare_pairing(application_id=application_id))


@mcp.tool()
def pc_ptmp_refresh_registration() -> str:
    """Stage an updated local PTMP registration. Re-add it manually in Packet Tracer's IPC configuration."""
    return json.dumps(refresh_registration())


@mcp.tool()
def pc_ptmp_status() -> str:
    """Authenticate with the locally paired Packet Tracer PTMP listener and report its live status."""
    return json.dumps(NativePtmpClient(load_settings(), Path.cwd()).invoke("STATUS"))


@mcp.tool()
def pc_ptmp_topology() -> str:
    """Read the live Packet Tracer topology through PTMP."""
    return json.dumps(NativePtmpClient(load_settings(), Path.cwd()).invoke("TOPOLOGY"))


@mcp.tool()
def pc_ptmp_add_device(device_type: str, model: str, x: float, y: float) -> str:
    """Create one device in the live logical workspace through the native PTMP adapter."""
    return json.dumps(NativePtmpClient(load_settings(), Path.cwd()).invoke("ADD_DEVICE", device_type, model, str(x), str(y)))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
