from __future__ import annotations

from enum import StrEnum
from ipaddress import IPv4Address, IPv4Network
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DeviceKind(StrEnum):
    ROUTER = "router"
    SWITCH = "switch"
    HOST = "host"
    SERVER = "server"
    ACCESS_POINT = "access_point"


class Device(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
    kind: DeviceKind
    model: str = "generic"
    x: int = 0
    y: int = 0


class Link(BaseModel):
    a: str
    b: str
    a_port: str = "auto"
    b_port: str = "auto"
    cable: Literal["auto", "copper_straight", "copper_cross", "serial", "fiber"] = "auto"

    @model_validator(mode="after")
    def endpoints_differ(self) -> "Link":
        if self.a == self.b:
            raise ValueError("a link cannot connect a device to itself")
        return self


class Routing(BaseModel):
    protocol: Literal["none", "static", "ospf", "eigrp", "rip"] = "none"
    ospf_process: int = Field(default=1, ge=1, le=65535)
    eigrp_as: int = Field(default=100, ge=1, le=65535)


class StaticRoute(BaseModel):
    """An explicit IOS static route; PacketCraft never guesses a next hop."""

    router: str
    destination: IPv4Network
    next_hop: IPv4Address | None = None
    exit_interface: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9/_.-]{0,63}$")
    administrative_distance: int = Field(default=1, ge=1, le=255)

    @model_validator(mode="after")
    def route_has_forwarding_target(self) -> "StaticRoute":
        if self.next_hop is None and self.exit_interface is None:
            raise ValueError("a static route needs next_hop or exit_interface")
        return self


class AddressAssignment(BaseModel):
    device: str
    interface: str
    address: IPv4Address
    prefix: int = Field(ge=0, le=32)


class TopologyPlan(BaseModel):
    name: str = Field(default="topology", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    devices: list[Device] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    routing: Routing = Field(default_factory=Routing)
    static_routes: list[StaticRoute] = Field(default_factory=list)
    addresses: list[AddressAssignment] = Field(default_factory=list)
    schema_version: Literal[1] = 1

    @field_validator("devices")
    @classmethod
    def unique_device_names(cls, devices: list[Device]) -> list[Device]:
        names = [device.name for device in devices]
        if len(names) != len(set(names)):
            raise ValueError("device names must be unique")
        return devices

    @model_validator(mode="after")
    def links_reference_devices(self) -> "TopologyPlan":
        names = {device.name for device in self.devices}
        missing = sorted({endpoint for link in self.links for endpoint in (link.a, link.b) if endpoint not in names})
        if missing:
            raise ValueError(f"links reference unknown device(s): {', '.join(missing)}")
        unknown_addresses = sorted({address.device for address in self.addresses if address.device not in names})
        if unknown_addresses:
            raise ValueError(f"addresses reference unknown device(s): {', '.join(unknown_addresses)}")
        interfaces = [(address.device, address.interface) for address in self.addresses]
        if len(interfaces) != len(set(interfaces)):
            raise ValueError("each device interface may have only one address assignment")
        devices_by_name = {device.name: device for device in self.devices}
        unknown_route_routers = sorted({route.router for route in self.static_routes if route.router not in names})
        if unknown_route_routers:
            raise ValueError(f"static routes reference unknown router(s): {', '.join(unknown_route_routers)}")
        non_routers = sorted({route.router for route in self.static_routes if devices_by_name[route.router].kind != DeviceKind.ROUTER})
        if non_routers:
            raise ValueError(f"static routes must belong to router device(s): {', '.join(non_routers)}")
        route_keys = [(route.router, route.destination, route.next_hop, route.exit_interface) for route in self.static_routes]
        if len(route_keys) != len(set(route_keys)):
            raise ValueError("static routes must be unique per router and forwarding target")
        return self


class Finding(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message: str


class ValidationReport(BaseModel):
    valid: bool
    findings: list[Finding]


def usable_network(cidr: str) -> IPv4Network:
    network = IPv4Network(cidr, strict=True)
    if network.version != 4:
        raise ValueError("only IPv4 allocation is supported in this milestone")
    return network
