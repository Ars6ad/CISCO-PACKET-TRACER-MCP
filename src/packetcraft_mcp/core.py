from __future__ import annotations

import hashlib
import itertools
import os
from collections import defaultdict, deque
from ipaddress import IPv4Network
from pathlib import Path

from .models import AddressAssignment, DeviceKind, Finding, TopologyPlan, ValidationReport, usable_network


def validate(plan: TopologyPlan) -> ValidationReport:
    findings: list[Finding] = []
    names = {d.name for d in plan.devices}
    if not plan.devices:
        findings.append(Finding(code="empty_topology", severity="error", message="a topology requires at least one device"))
    for link in plan.links:
        if link.a not in names or link.b not in names:
            findings.append(Finding(code="unknown_endpoint", severity="error", message=f"{link.a} ↔ {link.b} references an unknown device"))
    seen_addresses: dict[str, str] = {}
    for assignment in plan.addresses:
        owner = f"{assignment.device}:{assignment.interface}"
        if assignment.address in seen_addresses:
            findings.append(Finding(code="duplicate_ip", severity="error", message=f"{assignment.address} is used by {seen_addresses[assignment.address]} and {owner}"))
        seen_addresses[assignment.address] = owner
    routers = [d.name for d in plan.devices if d.kind == DeviceKind.ROUTER]
    dynamic_protocols = {"ospf", "eigrp", "rip"}
    if plan.routing.protocol in dynamic_protocols and len(routers) < 2:
        findings.append(Finding(code="routing_without_routers", severity="error", message="dynamic routing requires at least two routers"))
    summary = graph_summary(plan)
    if plan.devices and not plan.links and len(plan.devices) > 1:
        findings.append(Finding(code="disconnected", severity="warning", message="devices have no links"))
    if plan.routing.protocol in dynamic_protocols and not summary["connected"]:
        findings.append(Finding(code="routing_disconnected", severity="error", message="dynamic routing requires a connected topology"))
    if plan.routing.protocol == "static" and not plan.static_routes:
        findings.append(Finding(code="static_routes_missing", severity="error", message="static routing requires at least one explicit static route"))
    return ValidationReport(valid=not any(f.severity == "error" for f in findings), findings=findings)


def allocate_ipv4(plan: TopologyPlan, lan_pool: str = "10.10.0.0/16") -> TopologyPlan:
    """Assign /30 networks to router-router links and /24s to every host LAN.

    It is deterministic: identical plans always receive identical allocations.
    """
    pool = usable_network(lan_pool)
    if pool.prefixlen > 16:
        raise ValueError("lan_pool must be /16 or larger")
    devices = {d.name: d for d in plan.devices}
    router_links = [link for link in plan.links if devices[link.a].kind == DeviceKind.ROUTER and devices[link.b].kind == DeviceKind.ROUTER]
    adjacency: dict[str, list[str]] = defaultdict(list)
    for link in plan.links:
        adjacency[link.a].append(link.b); adjacency[link.b].append(link.a)
    router_lans = {
        router: sorted(node for node in adjacency[router] if devices[node].kind in {DeviceKind.HOST, DeviceKind.SERVER, DeviceKind.ACCESS_POINT})
        for router in (d.name for d in plan.devices if d.kind == DeviceKind.ROUTER)
    }
    lan_count = sum(bool(leafs) for leafs in router_lans.values())
    transit_blocks = max(1, (len(router_links) + 63) // 64) if router_links else 0
    available_lan_blocks = (1 << (24 - pool.prefixlen)) - transit_blocks
    if lan_count > available_lan_blocks:
        raise ValueError("lan_pool is too small for the requested transit and LAN networks")
    blocks = pool.subnets(new_prefix=24)
    transit_containers = list(itertools.islice(blocks, transit_blocks))
    lan_networks = blocks
    assignments: list[AddressAssignment] = []
    transit = itertools.chain.from_iterable(block.subnets(new_prefix=30) for block in transit_containers)
    used_interfaces: dict[str, set[str]] = defaultdict(set)
    next_interface: dict[str, int] = defaultdict(int)

    def interface_for(device: str, requested: str) -> str:
        if requested != "auto":
            used_interfaces[device].add(requested)
            return requested
        while f"G0/{next_interface[device]}" in used_interfaces[device]:
            next_interface[device] += 1
        interface = f"G0/{next_interface[device]}"
        used_interfaces[device].add(interface)
        next_interface[device] += 1
        return interface

    for link in sorted(router_links, key=lambda item: (item.a, item.b, item.a_port, item.b_port)):
        network = next(transit)
        first, second = list(network.hosts())[:2]
        assignments.extend([
            AddressAssignment(device=link.a, interface=interface_for(link.a, link.a_port), address=first, prefix=30),
            AddressAssignment(device=link.b, interface=interface_for(link.b, link.b_port), address=second, prefix=30),
        ])
    for router in sorted(router_lans):
        leafs = router_lans[router]
        if not leafs:
            continue
        network = next(lan_networks)
        assignments.append(AddressAssignment(device=router, interface=interface_for(router, "auto"), address=next(network.hosts()), prefix=24))
        for host_offset, node in enumerate(leafs, start=10):
            assignments.append(AddressAssignment(device=node, interface="NIC", address=list(network.hosts())[host_offset - 1], prefix=24))
    return plan.model_copy(update={"addresses": assignments})


def compile_ios(plan: TopologyPlan) -> dict[str, str]:
    report = validate(plan)
    if not report.valid:
        raise ValueError("cannot compile an invalid plan")
    by_device: dict[str, list[AddressAssignment]] = defaultdict(list)
    for address in plan.addresses:
        by_device[address.device].append(address)
    configs: dict[str, str] = {}
    static_routes_by_router: dict[str, list] = defaultdict(list)
    for route in plan.static_routes:
        static_routes_by_router[route.router].append(route)
    for device in plan.devices:
        if device.kind != DeviceKind.ROUTER:
            continue
        lines = [f"hostname {device.name}", "no ip domain-lookup"]
        networks: set[IPv4Network] = set()
        for assignment in sorted(by_device[device.name], key=lambda a: a.interface):
            network = IPv4Network(f"{assignment.address}/{assignment.prefix}", strict=False)
            networks.add(network)
            lines += [f"interface {assignment.interface}", f" ip address {assignment.address} {network.netmask}", " no shutdown", " exit"]
        if plan.routing.protocol == "static":
            for route in sorted(static_routes_by_router[device.name], key=lambda item: (str(item.destination), str(item.next_hop), item.exit_interface or "")):
                line = f"ip route {route.destination.network_address} {route.destination.netmask}"
                # IOS permits an exit interface, a next hop, or both.  When
                # both are supplied the interface precedes the next hop.
                if route.exit_interface is not None:
                    line += f" {route.exit_interface}"
                if route.next_hop is not None:
                    line += f" {route.next_hop}"
                if route.administrative_distance != 1:
                    line += f" {route.administrative_distance}"
                lines.append(line)
        elif plan.routing.protocol == "ospf":
            lines.append(f"router ospf {plan.routing.ospf_process}")
            lines.extend(f" network {network.network_address} {network.hostmask} area 0" for network in sorted(networks, key=str))
            lines.append(" exit")
        elif plan.routing.protocol == "eigrp":
            lines += [f"router eigrp {plan.routing.eigrp_as}", " no auto-summary"]
            lines.extend(f" network {network.network_address} {network.hostmask}" for network in sorted(networks, key=str))
            lines.append(" exit")
        elif plan.routing.protocol == "rip":
            lines += ["router rip", " version 2", " no auto-summary"]
            # PT IOS accepts the directly connected subnet here.
            lines.extend(f" network {network.network_address}" for network in sorted(networks, key=str))
            lines.append(" exit")
        lines.append("end")
        configs[device.name] = "\n".join(lines) + "\n"
    return configs


def graph_summary(plan: TopologyPlan) -> dict[str, object]:
    graph: dict[str, set[str]] = {device.name: set() for device in plan.devices}
    for link in plan.links:
        graph[link.a].add(link.b); graph[link.b].add(link.a)
    visited: set[str] = set(); components = 0
    for node in graph:
        if node in visited: continue
        components += 1; queue = deque([node]); visited.add(node)
        while queue:
            current = queue.popleft()
            for neighbor in graph[current] - visited:
                visited.add(neighbor); queue.append(neighbor)
    return {"devices": len(plan.devices), "links": len(plan.links), "components": components, "connected": components <= 1}


def save_plan(plan: TopologyPlan, directory: str = "projects") -> Path:
    destination = Path(directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{plan.name}.json"
    temporary = path.with_suffix(".json.tmp")
    payload = plan.model_dump_json(indent=2) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)
    return path


def load_plan(path: str) -> TopologyPlan:
    return TopologyPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))


def artifact_manifest(plan: TopologyPlan) -> dict[str, str]:
    payload = plan.model_dump_json(by_alias=True)
    return {"schema": "packetcraft/deployment-manifest/v1", "plan_sha256": hashlib.sha256(payload.encode()).hexdigest(), "plan": payload}
