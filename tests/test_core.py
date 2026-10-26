import pytest

from packetcraft_mcp.core import allocate_ipv4, compile_ios, graph_summary, validate
from packetcraft_mcp.models import Device, DeviceKind, Link, Routing, StaticRoute, TopologyPlan


def example() -> TopologyPlan:
    return TopologyPlan(name="lab", devices=[
        Device(name="R1", kind=DeviceKind.ROUTER), Device(name="R2", kind=DeviceKind.ROUTER),
        Device(name="PC1", kind=DeviceKind.HOST), Device(name="PC2", kind=DeviceKind.HOST),
    ], links=[Link(a="R1", b="R2"), Link(a="R1", b="PC1"), Link(a="R2", b="PC2")], routing=Routing(protocol="ospf"))


def test_allocate_is_deterministic_and_valid() -> None:
    first = allocate_ipv4(example())
    second = allocate_ipv4(example())
    assert first.addresses == second.addresses
    assert validate(first).valid
    assert len({item.address for item in first.addresses}) == len(first.addresses)


def test_ospf_compilation() -> None:
    config = compile_ios(allocate_ipv4(example()))["R1"]
    assert "router ospf 1" in config
    assert "no shutdown" in config


def test_eigrp_and_rip_compilation() -> None:
    eigrp_plan = example().model_copy(update={"routing": Routing(protocol="eigrp", eigrp_as=65001)})
    assert "router eigrp 65001" in compile_ios(allocate_ipv4(eigrp_plan))["R1"]
    rip_plan = example().model_copy(update={"routing": Routing(protocol="rip")})
    rip = compile_ios(allocate_ipv4(rip_plan))["R1"]
    assert "router rip" in rip and "version 2" in rip


def test_static_routes_are_explicit_and_compile_in_ios_order() -> None:
    plan = TopologyPlan(
        devices=[Device(name="R1", kind=DeviceKind.ROUTER)],
        routing=Routing(protocol="static"),
        static_routes=[StaticRoute(router="R1", destination="192.0.2.0/24", exit_interface="GigabitEthernet0/0", next_hop="10.0.0.2", administrative_distance=5)],
    )
    config = compile_ios(plan)["R1"]
    assert "ip route 192.0.2.0 255.255.255.0 GigabitEthernet0/0 10.0.0.2 5" in config


def test_static_routing_requires_an_explicit_route() -> None:
    plan = TopologyPlan(devices=[Device(name="R1", kind=DeviceKind.ROUTER)], routing=Routing(protocol="static"))
    assert any(item.code == "static_routes_missing" for item in validate(plan).findings)


def test_static_route_rejects_a_non_router_owner() -> None:
    with pytest.raises(ValueError, match="router device"):
        TopologyPlan(
            devices=[Device(name="PC1", kind=DeviceKind.HOST)],
            static_routes=[StaticRoute(router="PC1", destination="192.0.2.0/24", next_hop="10.0.0.1")],
        )


def test_graph_summary() -> None:
    assert graph_summary(example()) == {"devices": 4, "links": 3, "components": 1, "connected": True}


def test_custom_pool_is_respected_and_networks_do_not_overlap() -> None:
    plan = allocate_ipv4(example(), "172.20.0.0/16")
    assert all(str(assignment.address).startswith("172.20.") for assignment in plan.addresses)
    assigned_networks = {
        str(__import__("ipaddress").ip_network(f"{assignment.address}/{assignment.prefix}", strict=False))
        for assignment in plan.addresses
    }
    assert len(assigned_networks) == 3


def test_disconnected_dynamic_routing_is_an_error() -> None:
    plan = TopologyPlan(
        devices=[Device(name="R1", kind=DeviceKind.ROUTER), Device(name="R2", kind=DeviceKind.ROUTER)],
        routing=Routing(protocol="ospf"),
    )
    report = validate(plan)
    assert not report.valid
    assert any(finding.code == "routing_disconnected" for finding in report.findings)
