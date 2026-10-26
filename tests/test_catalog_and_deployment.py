import pytest

from packetcraft_mcp.catalog import list_models, resolve
from packetcraft_mcp.deployment import compile_actions, deployment_preview
from packetcraft_mcp.models import Device, DeviceKind, Link, TopologyPlan


def sample() -> TopologyPlan:
    return TopologyPlan(
        name="two-device",
        devices=[
            Device(name="R1", kind=DeviceKind.ROUTER, model="2911", x=100, y=100),
            Device(name="PC1", kind=DeviceKind.HOST, model="PC-PT", x=200, y=300),
        ],
        links=[Link(a="R1", b="PC1")],
    )


def test_catalog_contains_models_and_safe_defaults() -> None:
    assert any(item["model"] == "2911" for item in list_models())
    assert resolve(Device(name="R1", kind=DeviceKind.ROUTER)).model == "2911"
    with pytest.raises(ValueError, match="unsupported"):
        resolve(Device(name="R1", kind=DeviceKind.ROUTER, model="invented-router"))


def test_plan_compiles_to_deterministic_typed_actions() -> None:
    actions = compile_actions(sample())
    assert [item["type"] for item in actions] == ["create_device", "create_device", "connect_ports"]
    assert actions[-1]["arguments"] == {
        "a": "R1", "a_port": "GigabitEthernet0/0", "b": "PC1", "b_port": "FastEthernet0",
        "cable": "copper_straight",
    }
    assert deployment_preview(sample())["requires_explicit_approval"] is True


def test_plan_rejects_reused_or_unknown_ports() -> None:
    plan = TopologyPlan(
        devices=[Device(name="R1", kind=DeviceKind.ROUTER, model="2911"), Device(name="P1", kind=DeviceKind.HOST, model="PC-PT"), Device(name="P2", kind=DeviceKind.HOST, model="PC-PT")],
        links=[Link(a="R1", b="P1", a_port="GigabitEthernet0/0"), Link(a="R1", b="P2", a_port="GigabitEthernet0/0")],
    )
    with pytest.raises(ValueError, match="used"):
        compile_actions(plan)
