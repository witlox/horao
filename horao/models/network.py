# -*- coding: utf-8 -*-#
"""Networking equipment

This module contains the definition of networking equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in the state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional, TypeVar

import networkx as nx  # type: ignore
from packify import pack, unpack

from horao.models.components import Hardware
from horao.models.crdt import CRDTList, LastWriterWinsMap
from horao.models.osi_layers import LinkLayer, Port
from horao.models.status import DeviceStatus


class NetworkTopology(Enum):
    """Network topologies that should be able to manage."""

    # (low-radix) tree topology, or star-bus topology, in which star networks are interconnected via bus networks
    Tree = auto()
    # (low-radix, clos) scales to support huge data centers with uniform high capacity between servers,
    # performance isolation between services, and Ethernet layer-2 semantics
    VL2 = auto()
    # (high-radix, clos, AlFares) provides a scalable and cost-effective interconnection of servers in modern data
    # centers, interconnecting commodity switches in a fat-tree architecture achieves the full bisection bandwidth
    # of clusters
    FatTree = auto()
    # (high-radix, fat-tree) scalable, fault-tolerant layer 2 routing and forwarding protocol for data center
    # environments
    Portland = auto()
    # (high-radix, fat-tree) dynamic flow scheduling system that adaptively schedules a multi-stage switching
    # fabric to efficiently utilize aggregate network resources
    Hedera = auto()
    # (low-radix, recursive) a recursively defined structure, in which a high-level DCell is constructed from many
    # low-level DCells and DCells at the same level are fully connected with one another
    DCell = auto()
    # (low-radix, recursive) a new network architecture specifically designed for shipping-container based, modular
    # data centers
    BCube = auto()
    # (low-radix, recursive) a high performance interconnection structure to scale BCube-based containers to mega-data
    # centers
    MDCube = auto()
    # (low-radix, recursive) utilizes both ports and only the low-end commodity switches to form a scalable and highly
    # effective structure
    FiConn = auto()
    # (low-radix, flexible, fully optical) leverage runtime reconfigurable optical devices to dynamically changes its
    # topology and link capacities to adapt to dynamic traffic patterns
    OSA = auto()
    # (low-radix, flexible, hybrid) responsibility for traffic demand estimation and traffic de-multiplexing resides
    # in end hosts, making it compatible with existing packet switches
    CThrough = auto()
    # (low-radix, flexible, hybrid) hybrid electrical/optical switch architecture that can deliver significant
    # reductions in the number of switching elements, cabling, cost, and power consumption
    Helios = auto()
    # (high-radix, dragonfly) completely connected router groups, each pair of router groups has one or multiple
    # global optical connection, each pair of routers in the same router group has a single local connection
    DragonFly = auto()
    # (high-radix, dragonfly) enhanced DragonFly (1D), replaces the router group with a flattened butterfly 2D
    # connected group, where every two groups can be connected by one or multiple global connections
    DragonFlyPlus = auto()
    # (high-radix, dragonfly) enhanced DragonFly (1D), each router group contains two subgroups of switches: leaf
    # switches or spine switches. Spine switches are directly connected to spines of the other router groups, leaf
    # switches are connected to the spine switches in the same group
    Slingshot = auto()
    # No specific topology has been resolved
    Undefined = auto()


class NetworkType(Enum):
    Management = (
        auto()
    )  # administrative access to devices, analysis of state, health and configuration
    Control = (
        auto()
    )  # formulates and distributes guidance to the data plane, overseeing orchestration and coordination
    Data = (
        auto()
    )  # aka forwarding plane, policies, scaling and/or behavior triggers are generally executed here


class RouterType(Enum):
    Core = auto()
    Edge = auto()


class SwitchType(Enum):
    Access = auto()
    Distribution = auto()  # also known as Aggregation
    Core = auto()


class NetworkDevice(Hardware):
    def __init__(self, serial_number, name, model, number, ports: List[Port]):
        super().__init__(serial_number, name, model, number)
        self.ports = ports

    def __eq__(self, other: NetworkDevice) -> bool:
        return self.serial_number == other.serial_number and self.model == other.model

    def __ne__(self, other: NetworkDevice) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: NetworkDevice) -> bool:
        return self.number > other.number

    def __lt__(self, other):
        return self.number < other.number

    def __hash__(self) -> int:
        return hash((self.serial_number, self.model))

    def pack(self) -> bytes:
        return pack(
            [self.serial_number, self.name, self.model, self.number, self.ports]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> NetworkDevice:
        inject = {**globals()} if not inject else {**globals(), **inject}
        serial, name, model, number, ports = unpack(*data, inject=inject)
        return cls(serial, name, model, number, ports)


class NIC(NetworkDevice):
    def __init__(
        self, serial_number: str, name: str, model: str, number: int, ports: List[Port]
    ):
        super().__init__(serial_number, name, model, number, ports)

    def pack(self) -> bytes:
        return pack(
            [self.serial_number, self.name, self.model, self.number, self.ports]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> NIC:
        inject = {**globals()} if not inject else {**globals(), **inject}
        serial, name, model, number, ports = unpack(*data, inject=inject)
        return cls(serial, name, model, number, ports)


class Firewall(NetworkDevice):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        status: DeviceStatus,
        lan_ports: List[Port],
        wan_ports: Optional[List[Port]],
    ):

        super().__init__(serial_number, name, model, number, lan_ports)
        self.status = status
        self.wan_ports = wan_ports

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                1 if self.status == DeviceStatus.Up else 0,
                self.ports,
                self.wan_ports,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Firewall:
        inject = {**globals()} if not inject else {**globals(), **inject}
        serial, name, model, number, status, ports, wan_ports = unpack(
            data, inject=inject
        )
        return cls(
            serial_number=serial,
            name=name,
            model=model,
            number=number,
            status=DeviceStatus.Up if status == 1 else DeviceStatus.Down,
            lan_ports=ports,
            wan_ports=wan_ports,
        )


class Router(NetworkDevice):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        router_type: RouterType,
        status: DeviceStatus,
        lan_ports: List[Port],
        wan_ports: Optional[List[Port]],
    ):
        super().__init__(serial_number, name, model, number, lan_ports)
        self.router_type = router_type
        self.status = status
        self.wan_ports = wan_ports

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                1 if self.router_type == RouterType.Core else 2,
                1 if self.status == DeviceStatus.Up else 0,
                self.ports,
                self.wan_ports,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Router:
        inject = {**globals()} if not inject else {**globals(), **inject}
        (
            serial,
            name,
            model,
            number,
            router_type,
            status,
            ports,
            wan_ports,
        ) = unpack(data, inject=inject)
        return cls(
            serial_number=serial,
            name=name,
            model=model,
            number=number,
            router_type=RouterType.Core if router_type == 1 else RouterType.Edge,
            status=DeviceStatus.Up if status == 1 else DeviceStatus.Down,
            lan_ports=ports,
            wan_ports=wan_ports,
        )


class Switch(NetworkDevice):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        layer: LinkLayer,
        switch_type: SwitchType,
        status: DeviceStatus,
        managed: bool,
        lan_ports: List[Port],
        uplink_ports: Optional[List[Port]],
    ):
        super().__init__(serial_number, name, model, number, lan_ports)
        self.layer = layer
        self.switch_type = switch_type
        self.status = status
        self.managed = managed
        self.uplink_ports = uplink_ports

    def pack(self) -> bytes:
        return pack(
            [
                self.serial_number,
                self.name,
                self.model,
                self.number,
                2 if self.layer == LinkLayer.Layer2 else 3,
                (
                    1
                    if self.switch_type == SwitchType.Access
                    else 2 if self.switch_type == SwitchType.Distribution else 3
                ),
                1 if self.status == DeviceStatus.Up else 0,
                1 if self.managed else 0,
                self.ports,
                self.uplink_ports,
            ]
        )

    @classmethod
    def unpack(cls, data: bytes, /, *, inject: dict = None) -> Switch:
        inject = {**globals()} if not inject else {**globals(), **inject}
        (
            serial,
            name,
            model,
            number,
            layer,
            switch_type,
            status,
            managed,
            ports,
            uplink_ports,
        ) = unpack(data, inject=inject)
        return cls(
            serial_number=serial,
            name=name,
            model=model,
            number=number,
            layer=LinkLayer.Layer2 if layer == 2 else LinkLayer.Layer3,
            switch_type=(
                SwitchType.Access
                if switch_type == 1
                else SwitchType.Distribution if switch_type == 2 else SwitchType.Core
            ),
            status=DeviceStatus.Up if status == 1 else DeviceStatus.Down,
            managed=True if managed == 1 else False,
            lan_ports=ports,
            uplink_ports=uplink_ports,
        )


T = TypeVar("T", bound=NetworkDevice)


class NetworkList(CRDTList[T]):
    def __init__(
        self,
        devices: List[T] = None,
        items: LastWriterWinsMap = None,
        inject=None,
    ):
        super().__init__(devices, items, inject=inject)
