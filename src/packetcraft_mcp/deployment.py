"""Compile validated topology plans into typed Script Module actions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .catalog import normalize_cable, resolve
from .core import validate
from .models import Link, TopologyPlan


def compile_actions(plan: TopologyPlan) -> list[dict[str, Any]]:
    """Make an explicit, deterministic, no-code deployment action list.

    The output can be previewed, reviewed, and then passed unchanged to the
    Script Module. Ports marked ``auto`` are resolved against the PacketCraft
    model catalog before Packet Tracer sees the job.
    """
    report = validate(plan)
    errors = [finding.message for finding in report.findings if finding.severity == "error"]
    if errors:
        raise ValueError("cannot deploy invalid plan: " + "; ".join(errors))
    models = {device.name: resolve(device) for device in plan.devices}
    used: dict[str, set[str]] = defaultdict(set)
    actions: list[dict[str, Any]] = []
    for device in plan.devices:
        model = models[device.name]
        actions.append({"type": "create_device", "arguments": {
            "kind": device.kind.value, "model": model.model, "name": device.name,
            "x": device.x, "y": device.y,
        }})
    for link in plan.links:
        a_port = _port_for(link, "a", models[link.a].ports, used[link.a])
        b_port = _port_for(link, "b", models[link.b].ports, used[link.b])
        used[link.a].add(a_port); used[link.b].add(b_port)
        actions.append({"type": "connect_ports", "arguments": {
            "a": link.a, "a_port": a_port, "b": link.b, "b_port": b_port,
            "cable": normalize_cable(link.cable, models[link.a].kind, models[link.b].kind),
        }})
    return actions


def deployment_preview(plan: TopologyPlan) -> dict[str, Any]:
    actions = compile_actions(plan)
    return {
        "schema": "packetcraft/deployment-preview/v1",
        "topology": plan.name,
        "device_count": len(plan.devices),
        "link_count": len(plan.links),
        "actions": actions,
        "requires_explicit_approval": True,
    }


def _port_for(link: Link, endpoint: str, available: tuple[str, ...], already_used: set[str]) -> str:
    requested = link.a_port if endpoint == "a" else link.b_port
    if requested != "auto":
        if requested not in available:
            raise ValueError(f"{getattr(link, endpoint)!r} has no catalogued port {requested!r}")
        if requested in already_used:
            raise ValueError(f"port {getattr(link, endpoint)}:{requested} is used by more than one link")
        return requested
    for port in available:
        if port not in already_used:
            return port
    raise ValueError(f"no free catalogued ports remain for {getattr(link, endpoint)!r}")
