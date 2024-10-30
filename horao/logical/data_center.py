# -*- coding: utf-8 -*-#
"""Data Center composites"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Tuple

import networkx as nx
from networkx.algorithms.traversal import bfs_edges
from networkx.classes import Graph

from horao.conceptual.crdt import LastWriterWinsMap
from horao.conceptual.decorators import instrument_class_function
from horao.physical.component import Disk
from horao.physical.composite import Blade, Cabinet, Chassis, Server
from horao.physical.computer import Computer
from horao.physical.network import (
    NIC,
    Firewall,
    NetworkDevice,
    NetworkTopology,
    NetworkType,
    Port,
    Router,
    Switch,
)
from horao.physical.status import DeviceStatus


class DataCenter:
    """Data Center model
    Behaves as a dictionary
    Each pair of the dictionary is a row in the data center
    The key is the row number, the value is a list of cabinets
    """

    def __init__(
        self,
        name: str,
        number: int,
        rows: LastWriterWinsMap = None,
        items: Dict[int, List[Cabinet]] = None,
    ) -> None:
        """
        Initialize a data center
        :param name: unique name
        :param number: unique number referring to potential AZ
        :param rows: optional LastWriterWinsMap of rows
        :param items: optional dictionary of rows (number, list of cabinets)
        """
        self.log = logging.getLogger(__name__)
        self.name = name
        self.number = number
        self.rows = LastWriterWinsMap() if not rows else rows
        if items:
            for k, v in items.items():
                self.rows.set(k, v, hash(k))

    def clear(self) -> None:
        self.rows = LastWriterWinsMap()

    @instrument_class_function(name="copy", level=logging.DEBUG)
    def copy(self) -> Dict[int, List[Cabinet]]:
        result = {}
        for k, v in self.rows.read():
            result[k] = list(iter(v))
        return result

    @instrument_class_function(name="has_key", level=logging.DEBUG)
    def has_key(self, k: int) -> bool:
        for key, _ in self.rows.read():
            if key == k:
                return True
        return False

    def update(self, key: int, value: List[Cabinet]) -> None:
        self.rows.set(key, value, hash(key))

    def keys(self) -> List[int]:
        return [k for k, _ in self.rows.read()]

    def values(self) -> List[List[Cabinet]]:
        return [v for _, v in self.rows.read()]

    def items(self) -> List[Tuple[int, List[Cabinet]]]:
        return [(k, v) for k, v in self.rows.read()]

    @instrument_class_function(name="pop", level=logging.DEBUG)
    def pop(self, key: int) -> List[Cabinet]:
        for k, v in self.rows.read():
            if k == key:
                self.rows.unset(key, key)
                return v.value
        raise KeyError(f"Key {key} not found")

    def __eq__(self, other: DataCenter) -> bool:
        return self.name == other.name

    def __ne__(self, other: DataCenter) -> bool:
        return not self == other

    def __setitem__(self, key: int, item: List[Cabinet]) -> None:
        self.rows.set(key, item, hash(key))

    @instrument_class_function(name="getitem", level=logging.DEBUG)
    def __getitem__(self, key) -> List[Cabinet]:
        for k, v in self.rows.read().items():
            if k == key:
                return v.value
        raise KeyError(f"Key {key} not found")

    @instrument_class_function(name="delitem", level=logging.DEBUG)
    def __delitem__(self, key) -> None:
        for k, v in self.rows.read().items():
            if k == key:
                self.rows.unset(key, hash(key))
                return
        raise KeyError(f"Key {key} not found")

    def __repr__(self) -> str:
        return f"DataCenter({self.number}, {self.name}))"

    def __len__(self) -> int:
        return len(self.rows.read())

    def __contains__(self, cabinet: Cabinet) -> bool:
        for _, v in self.rows.read().items():
            if cabinet in v:
                return True
        return False

    def __iter__(self) -> Iterable[Tuple[int, List[Cabinet]]]:
        for k, v in self.items():
            yield k, v

    def __hash__(self) -> int:
        return hash((self.name, self.number))

    @staticmethod
    @instrument_class_function(name="move_server", level=logging.DEBUG)
    def move_server(server: Server, from_cabinet: Cabinet, to_cabinet: Cabinet) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_cabinet: from
        :param to_cabinet: to
        :return: None
        :raises: ValueError if you try to remove a server that doesn't exist
        """
        if not server in from_cabinet.servers:
            raise ValueError("Cannot move servers that are not installed.")
        from_cabinet.servers.remove(server)
        to_cabinet.servers.append(server)

    @staticmethod
    @instrument_class_function(name="move_chassis", level=logging.DEBUG)
    def move_chassis_server(
        server: Server, from_chassis: Chassis, to_chassis: Chassis
    ) -> None:
        """
        Move a server from one cabinet to another
        :param server: server to move
        :param from_chassis: from
        :param to_chassis: to
        :return: None
        :raises: ValueError if you try to remove a server that doesn't exist
        """
        if not server in from_chassis.servers:
            raise ValueError("Cannot move servers that are not installed.")
        from_chassis.servers.remove(server)
        to_chassis.servers.append(server)

    @staticmethod
    @instrument_class_function(name="move_blade", level=logging.DEBUG)
    def move_blade(blade: Blade, from_chassis: Chassis, to_chassis: Chassis) -> None:
        """
        Move a server from one chassis to another
        :param blade: blade to move
        :param from_chassis: from
        :param to_chassis: to
        :return: None
        :raises: ValueError if you try to remove a blade that is not installed
        """
        if not blade in from_chassis.blades:
            raise ValueError("Cannot move blades that are not installed.")
        from_chassis.blades.remove(blade)
        to_chassis.blades.append(blade)

    @staticmethod
    @instrument_class_function(name="swap_disk", level=logging.DEBUG)
    def swap_disk(
        server: Server, old_disk: Optional[Disk], new_disk: Optional[Disk]
    ) -> None:
        """
        Swap a (broken) disk in a server
        :param server: server to swap disk from/in
        :param old_disk: old disk to remove (if any)
        :param new_disk: new disk to add (if any)
        :return: None
        :raises: ValueError if you try to remove a disk that doesn't exist
        """
        if new_disk is not None:
            server.disks.append(new_disk)
        if old_disk:
            if not server.disks:
                raise ValueError("Cannot remove disks that are not installed.")
            server.disks.remove(old_disk)

    def fetch_server_nic(
        self, row: int, cabinet: int, server: int, nic: int, chassis: Optional[int]
    ) -> NIC:
        """
        Fetch a port from a server NIC
        :param row: Row in DC
        :param cabinet: Cabinet in Row
        :param server: Server in Cabinet/Chassis
        :param nic: NIC in Server
        :param chassis: Chassis in Cabinet (optional)
        :return: NIC object
        :raises: ValueError if any of the indexes are out of bounds
        """
        if row > len(self):
            raise ValueError("Row does not exist")
        if cabinet > len(self.rows.read()):
            raise ValueError("Cabinet does not exist")
        if chassis is not None and chassis > len(
            self.rows.read()[row - 1][cabinet - 1].chassis
        ):
            raise ValueError("Chassis does not exist")
        if server > len(self.rows.read()[row][cabinet - 1].servers):
            raise ValueError("Server does not exist")
        if nic > len(self.rows.read()[row][cabinet - 1].servers[server - 1].nics):
            raise ValueError("NIC does not exist")
        return self.rows.read()[row][cabinet - 1].servers[server - 1].nics[nic - 1]


class DataCenterNetwork:
    """Data Center Network model"""

    def __init__(
        self,
        name: str,
        network_type: NetworkType,
        graph: Optional[Graph] = None,
        high_speed_network: Optional[bool] = None,
    ) -> None:
        """
        Initialize a data center network
        :param name: network name
        :param network_type: type of network
        :param high_speed_network: this is a high speed, low latency network
        """
        self.graph = graph if graph else nx.Graph()
        self.name = name
        self.network_type = network_type
        self.hsn = high_speed_network if high_speed_network else False

    def __eq__(self, other: DataCenterNetwork):
        return self.name == other.name and self.network_type == other.network_type

    def __hash__(self):
        return hash((self.name, self.network_type))

    @instrument_class_function(name="add", level=logging.DEBUG)
    def add(self, network_device: NetworkDevice | Computer) -> None:
        """
        Add a network device to the network
        :param network_device: device to add
        :return: None
        """
        self.graph.add_node(network_device)

    def add_multiple(self, network_devices: List[NetworkDevice]) -> None:
        """
        Add multiple network devices to the network at once
        :param network_devices: list of network devices
        :return: None
        """
        for device in network_devices:
            self.add(device)

    @instrument_class_function(name="link", level=logging.DEBUG)
    def link(self, left: NetworkDevice, right: NetworkDevice | Computer) -> None:
        """
        Link two network devices, if they are switches, they are connected via uplink ports, if they are routers or
        firewalls, they are connected via lan ports. We use 'the first' lan port if no uplink ports are available. We
        currently do not keep count of port usage. There is currently no explicit link that is tracked for the
        connection, we 'simply' pick the first available port. For computers we iterate through the NICs to find the
        first available port.
        :param left: device (if uplink ports exist, they are used to connect to other devices)
        :param right: device (lan ports are used to connect to other devices)
        :return: None
        :raises ValueError: if no free ports are available on either device.
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
        if isinstance(right, NetworkDevice):
            right_port = next(iter([r for r in right.ports if not r.connected]), None)
        else:
            # we assume that if it isn't a network device, it is a computer
            right_port = next(
                iter([r for n in right.nics for r in n.ports if not r.connected]), None
            )
        if not right_port:
            raise ValueError(
                f"No free ports available on {right.name} ({right.number}:{right.serial_number})"
            )
        link_free_ports(left_port, right_port)

    @instrument_class_function(name="unlink", level=logging.DEBUG)
    def unlink(self, left: NetworkDevice, right: NetworkDevice | Computer) -> None:
        """
        Unlink two network devices, if the device is composed of multiple ports, we
        assume that the first connected port needs disconnecting. For computers we
        iterate through all nics to find the first connected port.
        :param left: network device
        :param right: network device or computer
        :return: None
        :raises ValueError: if no connected ports are available on either device
        """
        self.graph.remove_edge(left, right)
        if isinstance(left, Switch) and left.uplink_ports and any(left.uplink_ports):
            left_port = next(iter([l for l in left.uplink_ports if l.connected]), None)
        else:
            left_port = next(iter([l for l in left.ports if l.connected]), None)
        if isinstance(right, NetworkDevice):
            right_port = next(iter([r for r in right.ports if r.connected]), None)
        else:
            # we assume that if it isn't a network device, it is a computer
            right_port = next(
                iter([r for n in right.nics for r in n.ports if r.connected]), None
            )
        if not left_port or not right_port:
            raise ValueError(
                f"could not determine connected ports for {left.name} and {right.name}"
            )
        left_port.connected = False
        left_port.status = DeviceStatus.Down
        right_port.connected = False
        right_port.status = DeviceStatus.Down

    @instrument_class_function(name="toggle", level=logging.DEBUG)
    def toggle(self, device: NetworkDevice | Computer) -> None:
        """
        Toggle the status of a device and all connected ports
        :param device: network device or computer
        :return: None
        """
        n: NetworkDevice | Computer
        for n in self.graph.neighbors(device):
            if isinstance(n, Switch) and n.uplink_ports and any(n.uplink_ports):
                left_port = next(iter([l for l in n.uplink_ports if l.connected]), None)
            elif isinstance(n, Computer):
                left_port = next(
                    iter([l for ni in n.nics for l in ni if l.connected]), None
                )
            else:
                left_port = next(iter([l for l in n.ports if l.connected]), None)
            if left_port:
                left_port.status = DeviceStatus.Down
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
        elif isinstance(device, Computer):
            for nic in device.nics:
                for port in nic:
                    port.status = (
                        DeviceStatus.Down
                        if port.status == DeviceStatus.Up
                        else DeviceStatus.Up
                    )

    def get_topology(self) -> NetworkTopology:
        """
        Determine the topology of the network
        :return: topology (currently tree or undefined)
        """
        if nx.is_tree(self.graph):
            return NetworkTopology.Tree
        return NetworkTopology.Undefined

    def nodes(self) -> List[NetworkDevice]:
        """
        Return all network devices in the network
        :return: List of network devices
        """
        return list(self.graph.nodes)

    def computers(self) -> List[Computer]:
        """
        Return all computers in the network
        :return: List of Computer (Server or Module)
        """
        return [n for n in self.graph.nodes if isinstance(n, Computer)]

    def is_hsn(self) -> bool:
        """
        Determine if the network is a high speed network
        :return: bool
        """
        return self.hsn

    def links_from_graph(self, graph: Graph) -> None:
        """
        Add links from a hash representation graph to the network,
        note that all network devices need to be present.
        :param graph: graph with links
        :return: None
        :raises ValueError: if network devices are not present in the graph
        """
        for left, right in graph.edges():
            left_node = next(
                iter([n for n in self.graph.nodes if int(hash(n)) == int(left)]), None
            )
            right_node = next(
                iter([n for n in self.graph.nodes if int(hash(n)) == int(right)]), None
            )
            if not left_node or not right_node:
                raise ValueError("Could not find network devices in graph")
            self.link(left_node, right_node)

    def hash_graph(self) -> Optional[Graph]:
        """
        Generate a Graph without the actual objects, but with the hash of the objects
        :return: graph or None if no nodes are present
        """
        if len(self.nodes()) == 0:
            return None
        graph = nx.Graph()
        for left, right in self.graph.edges():
            if hash(left) not in graph.nodes:
                graph.add_node(hash(left))
            if right not in graph.nodes:
                graph.add_node(hash(right))
            graph.add_edge(hash(left), hash(right))
        return graph
