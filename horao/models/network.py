# -*- coding: utf-8 -*-#
# Networking equipment
#
# This module contains the definition of networking equipment (hardware) and their properties.
# We assume that 'faulty' equipment state is either up or down, it should be handled in the state machine, not here.
# Also we assume that these data structures are not very prone to change, given that this implies a manual activity.

from enum import Enum, auto


from status import DeviceStatus
from osi_layers import Port, LinkLayer


class NetworkTopology(Enum):
    Tree = (
        auto()
    )  # (low-radix) tree topology, or star-bus topology, in which star networks are interconnected via bus networks
    VL2 = (
        auto()
    )  # (low-radix, clos) scales to support huge data centers with uniform high capacity between servers, performance isolation between services, and Ethernet layer-2 semantics
    FatTree = (
        auto()
    )  # (high-radix, clos, AlFares) provides a scalable and cost-effective interconnection of servers in modern data centers, interconnecting commodity switches in a fat-tree architecture achieves the full bisection bandwidth of clusters
    Portland = (
        auto()
    )  # (high-radix, fat-tree) scalable, fault tolerant layer 2 routing and forwarding protocol for data center environments
    Hedera = (
        auto()
    )  # (high-radix, fat-tree) dynamic flow scheduling system that adaptively schedules a multi-stage switching fabric to efficiently utilize aggregate network resources
    DCell = (
        auto()
    )  # (low-radix, recursive) a recursively defined structure, in which a high-level DCell is constructed from many low-level DCells and DCells at the same level are fully connected with one another
    BCube = (
        auto()
    )  # (low-radix, recursive) a new network architecture specifically designed for shipping-container based, modular data centers
    MDCube = (
        auto()
    )  # (low-radix, recursive) a high performance interconnection structure to scale BCube-based containers to mega-data centers
    FiConn = (
        auto()
    )  # (low-radix, recursive) utilizes both ports and only the low-end commodity switches to form a scalable and highly effective structure
    OSA = (
        auto()
    )  # (low-radix, flexible, fully optical) leverage runtime reconfigurable optical devices to dynamically changes its topology and link capacities to adapt to dynamic traffic patterns
    CThrough = (
        auto()
    )  # (low-radix, flexible, hybrid) responsibility for traffic demand estimation and traffic demultiplexing resides in end hosts, making it compatible with existing packet switches
    Helios = (
        auto()
    )  # (low-radix, flexible, hybrid) hybrid electrical/optical switch architecture that can deliver significant reductions in the number of switching elements, cabling, cost, and power consumption
    DragonFly = (
        auto()
    )  # (high-radix, dragonfly) completely connected router groups, each pair of router groups has one or multiple global optical connection, each pair of routers in the same router group has a single local connection
    Slingshot = (
        auto()
    )  # (high-radix, dragonfly) enhanced DragonFly (1D), replaces the router group with a flattened butterfly 2D connected group, where every two groups can be connected by one or multiple global connections
    DragonFlyPlus = (
        auto()
    )  # (high-radix, dragonfly) enhanced DragonFly (1D), each router group contains two sub-groups of switches: leaf switches or spine switches. Spine switches are directly connected to spines of the other router groups, leaf switches are connected to the spine switches in the same group
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
    Distribution = auto()  # also know as Aggregation
    Core = auto()


class Firewall:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        status: DeviceStatus,
        lan_ports: list[Port],
        wan_ports: list[Port],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.status = status
        self.lan_ports = lan_ports
        self.wan_ports = wan_ports


class Router:
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        router_type: RouterType,
        status: DeviceStatus,
        lan_ports: list[Port],
        wan_ports: list[Port],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.router_type = router_type
        self.status = status
        self.lan_ports = lan_ports
        self.wan_ports = wan_ports


class Switch:
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
        lan_ports: list[Port],
        uplink_ports: list[Port],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.layer = layer
        self.switch_type = switch_type
        self.status = status
        self.managed = managed
        self.lan_ports = lan_ports
        self.uplink_ports = uplink_ports


class DataCenterNetwork:
    def __init__(
        self,
        name: str,
        network_type: NetworkType,
        switches: list[Switch],
        routers: list[Router],
        firewalls: list[Firewall],
    ):
        self.name = name
        self.network_type = network_type
        self.switches = switches
        self.routers = routers
        self.firewalls = firewalls
        self.topology = NetworkTopology.Undefined

    def get_topology(self) -> NetworkTopology:
        return NetworkTopology.Undefined