# -*- coding: utf-8 -*-#
"""Networking equipment

This module contains the definition of networking equipment (hardware) and their properties.
We assume that 'faulty' equipment state is either up or down, it should be handled in the state machine, not here.
Also, we assume that these data structures are not very prone to change, given that this implies a manual activity.
"""
import logging
from enum import Enum, auto
from typing import List, Optional

import networkx as nx  # type: ignore


from horao.models.status import DeviceStatus
from horao.models.osi_layers import Port, LinkLayer


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


class NetworkDevice:
    def __init__(self, serial_number, name, model, number, ports: List[Port]):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.ports = ports


class NIC(NetworkDevice):
    def __init__(
        self, serial_number: str, name: str, model: str, number: int, ports: List[Port]
    ):
        super().__init__(serial_number, name, model, number, ports)


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


class DataCenterNetwork:
    def __init__(
        self,
        name: str,
        network_type: NetworkType,
    ):
        self.graph = nx.Graph()
        self.name = name
        self.network_type = network_type

    def add(self, network_device: NetworkDevice) -> None:
        self.graph.add_node(network_device)

    def add_multiple(self, network_devices: list[NetworkDevice]) -> None:
        for network_device in network_devices:
            self.add(network_device)

    def link(self, left: NetworkDevice, right: NetworkDevice) -> None:
        """
        Link two network devices, if they are switches, they are connected via uplink ports, if they are routers or
        firewalls, they are connected via lan ports. We use 'the first' lan port if no uplink ports are available. We
        currently do not keep count of port usage. There is currently no explicit link that is tracked for the
        connection, we 'simply' pick the first available port.
        :param left: device (if uplink ports exist, they are used to connect to other devices)
        :param right: device (lan ports are used to connect to other devices)
        :return: None
        :raises: ValueError if no free ports are available on either device.
        """

        def link_free_ports(lp: Port, rp: Port) -> None:
            self.graph.add_edge(left, right)
            lp.connected = True
            rp.connected = True
            lp.status = DeviceStatus.Up
            rp.status = DeviceStatus.Up

        if isinstance(left, Switch) and left.uplink_ports and any(left.uplink_ports):
            left_port = next(
                iter([l for l in left.uplink_ports if not l.connected]), None
            )
        else:
            left_port = next(iter([l for l in left.ports if not l.connected]), None)
        if not left_port:
            raise ValueError(
                f"No free ports available on {left.name} ({left.number}:{left.serial_number})"
            )
        right_port = next(iter([r for r in right.ports if not r.connected]), None)
        if not right_port:
            raise ValueError(
                f"No free ports available on {right.name} ({right.number}:{right.serial_number})"
            )
        link_free_ports(left_port, right_port)

    def unlink(self, left: NetworkDevice, right: NetworkDevice) -> None:
        self.graph.remove_edge(left, right)
        if isinstance(left, Switch) and left.uplink_ports and any(left.uplink_ports):
            left_port = next(iter([l for l in left.uplink_ports if l.connected]), None)
        else:
            left_port = next(iter([l for l in left.ports if l.connected]), None)
        right_port = next(iter([r for r in right.ports if r.connected]), None)
        if not left_port or not right_port:
            raise ValueError(
                f"could not determine connected ports for {left.name} and {right.name}"
            )
        left_port.connected = False
        left_port.status = DeviceStatus.Down
        right_port.connected = False
        right_port.status = DeviceStatus.Down

    def toggle(self, device: NetworkDevice) -> None:
        n: NetworkDevice
        for n in self.graph.neighbors(device):
            if isinstance(n, Switch) and n.uplink_ports and any(n.uplink_ports):
                left_port = next(iter([l for l in n.uplink_ports if l.connected]), None)
            else:
                left_port = next(iter([l for l in n.ports if l.connected]), None)
            if left_port:
                left_port.status = DeviceStatus.Down
            else:
                logging.warning(
                    f"could not determine connected port for {n.name} to {device.name}"
                )
        for port in device.ports:
            port.status = (
                DeviceStatus.Down if port.status == DeviceStatus.Up else DeviceStatus.Up
            )
        if isinstance(device, Switch):
            device.status = (
                DeviceStatus.Down
                if device.status == DeviceStatus.Up
                else DeviceStatus.Up
            )
            if device.uplink_ports:
                for port in device.uplink_ports:
                    port.status = (
                        DeviceStatus.Down
                        if port.status == DeviceStatus.Up
                        else DeviceStatus.Up
                    )
        elif isinstance(device, Router):
            device.status = (
                DeviceStatus.Down
                if device.status == DeviceStatus.Up
                else DeviceStatus.Up
            )
            if device.wan_ports:
                for port in device.wan_ports:
                    port.status = (
                        DeviceStatus.Down
                        if port.status == DeviceStatus.Up
                        else DeviceStatus.Up
                    )
        elif isinstance(device, Firewall):
            device.status = (
                DeviceStatus.Down
                if device.status == DeviceStatus.Up
                else DeviceStatus.Up
            )
            if device.wan_ports:
                for port in device.wan_ports:
                    port.status = (
                        DeviceStatus.Down
                        if port.status == DeviceStatus.Up
                        else DeviceStatus.Up
                    )

    def get_topology(self) -> NetworkTopology:
        if nx.is_tree(self.graph):
            return NetworkTopology.Tree
        return NetworkTopology.Undefined
