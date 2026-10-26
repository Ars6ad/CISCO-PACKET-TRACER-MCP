"""Small, versioned Packet Tracer 9 device and cable facts.

These facts are deliberately owned by PacketCraft rather than copied from an
extension.  They are the first catalog slice needed to turn a declarative plan
into safe, explicit Script Module actions.  New models belong here only after
their ports have been checked against Packet Tracer.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Device, DeviceKind


@dataclass(frozen=True, slots=True)
class DeviceModel:
    model: str
    kind: DeviceKind
    device_type: int
    ports: tuple[str, ...]


def _fast(count: int) -> tuple[str, ...]:
    return tuple(f"FastEthernet0/{number}" for number in range(1, count + 1))


MODELS: tuple[DeviceModel, ...] = (
    DeviceModel("1941", DeviceKind.ROUTER, 0, ("GigabitEthernet0/0", "GigabitEthernet0/1")),
    DeviceModel("2901", DeviceKind.ROUTER, 0, ("GigabitEthernet0/0", "GigabitEthernet0/1")),
    DeviceModel("2911", DeviceKind.ROUTER, 0, ("GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet0/2")),
    DeviceModel("ISR4321", DeviceKind.ROUTER, 0, ("GigabitEthernet0/0/0", "GigabitEthernet0/0/1")),
    DeviceModel("ISR4331", DeviceKind.ROUTER, 0, ("GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "GigabitEthernet0/0/2")),
    DeviceModel("Router-PT", DeviceKind.ROUTER, 0, ("FastEthernet0/0", "FastEthernet0/1")),
    DeviceModel("2960-24TT", DeviceKind.SWITCH, 1, _fast(24) + ("GigabitEthernet0/1", "GigabitEthernet0/2")),
    DeviceModel("3560-24PS", DeviceKind.SWITCH, 16, _fast(24) + ("GigabitEthernet0/1", "GigabitEthernet0/2")),
    DeviceModel("Switch-PT", DeviceKind.SWITCH, 1, _fast(8)),
    DeviceModel("PC-PT", DeviceKind.HOST, 8, ("FastEthernet0",)),
    DeviceModel("Laptop-PT", DeviceKind.HOST, 17, ("FastEthernet0",)),
    DeviceModel("Server-PT", DeviceKind.SERVER, 9, ("FastEthernet0",)),
    DeviceModel("AccessPoint-PT", DeviceKind.ACCESS_POINT, 7, ("Port 0",)),
)
BY_MODEL = {item.model.casefold(): item for item in MODELS}
DEFAULT_MODEL = {
    DeviceKind.ROUTER: "2911",
    DeviceKind.SWITCH: "2960-24TT",
    DeviceKind.HOST: "PC-PT",
    DeviceKind.SERVER: "Server-PT",
    DeviceKind.ACCESS_POINT: "AccessPoint-PT",
}

_CABLE_ALIASES = {
    "auto": "auto",
    "copper_straight": "copper_straight",
    "copper_cross": "copper_cross",
    "fiber": "fiber",
    "serial": "serial",
}


def resolve(device: Device) -> DeviceModel:
    """Return a model matching a plan device, supplying only documented defaults."""
    candidate = DEFAULT_MODEL[device.kind] if device.model == "generic" else device.model
    model = BY_MODEL.get(candidate.casefold())
    if model is None:
        supported = ", ".join(item.model for item in MODELS)
        raise ValueError(f"unsupported Packet Tracer model {candidate!r}; supported models: {supported}")
    if model.kind != device.kind:
        raise ValueError(f"model {model.model!r} is a {model.kind.value}, not a {device.kind.value}")
    return model


def list_models() -> list[dict[str, object]]:
    return [
        {"model": item.model, "kind": item.kind.value, "device_type": item.device_type, "ports": list(item.ports)}
        for item in MODELS
    ]


def normalize_cable(cable: str, left: DeviceKind, right: DeviceKind) -> str:
    if cable not in _CABLE_ALIASES:
        raise ValueError(f"unsupported cable type: {cable}")
    if cable != "auto":
        return _CABLE_ALIASES[cable]
    # Packet Tracer's AUTO cable is safest for special interfaces. For standard
    # Ethernet paths use an explicit predictable selection in preview output.
    if {left, right} == {DeviceKind.ROUTER, DeviceKind.ROUTER}:
        return "copper_cross"
    return "copper_straight"
