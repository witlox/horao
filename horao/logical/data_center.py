# -*- coding: utf-8 -*-#
"""Data Center composites"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import networkx as nx  # type: ignore
from networkx.classes import Graph  # type: ignore

from horao.conceptual.crdt import LastWriterWinsMap
from horao.conceptual.decorators import instrument_class_function
from horao.conceptual.support import Update
from horao.physical.composite import Cabinet
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
        rows: Optional[LastWriterWinsMap] = None,
        items: Optional[Dict[int, List[Cabinet]]] = None,
        listeners: Optional[List[Callable]] = None,
    ) -> None:
        """
        Initialize a data center
        :param name: unique name
        :param number: unique number referring to potential AZ
        :param rows: optional LastWriterWinsMap of rows
        :param items: optional dictionary of rows (number, list of cabinets)
        :param listeners: optional list of listeners
        """
        self.log = logging.getLogger(__name__)
        self.name = name
        self.number = number
        self.listeners = listeners if listeners else []
        self.rows = (
            LastWriterWinsMap(listeners=[self.invoke_listeners]) if not rows else rows
        )
        if items:
            for k, v in items.items():
                self.rows.set(k, v, hash(k))  # type: ignore
        self.changes: List[Update] = []

    def add_listeners(self, listener: Callable) -> None:
        """
        Adds an async listener that is called on each update.
        :param listener: Callable
        :return: None
        """
        if not listener in self.listeners:
            self.listeners.append(listener)

    def remove_listeners(self, listener: Callable) -> None:
        """
        Removes a listener if it was previously added.
        :param listener: Callable
        :return: None
        """
        if listener in self.listeners:
            self.listeners.remove(listener)

    def invoke_listeners(self, changes: Optional[List] = None) -> None:
        """
        Invokes all event listeners.
        :param changes: list of changes
        :return: None
        """
        if changes:
            if isinstance(changes, List):
                self.changes.extend(changes)
            else:
                self.changes.append(changes)  # type: ignore
        for listener in self.listeners:
            listener(changes)

    def clear_changes(self) -> None:
        """
        Clear the changes
        :return: None
        """
        for _, v in self.rows.read().items():
            for cabinet in v:
                for server in cabinet.servers:
                    server.disks.clear_history()
                cabinet.servers.clear_history()
                for chassis in cabinet.chassis:
                    for blade in chassis.blades:
                        for node in blade.nodes:
                            for module in node.modules:
                                module.disks.clear_history()
                            node.modules.clear_history()
                        blade.nodes.clear_history()
                    chassis.blades.clear_history()
                cabinet.chassis.clear_history()
                cabinet.switches.clear_history()
        self.changes = []

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
        if key in self.keys():
            self.__delitem__(key)
        self.__setitem__(key, value, hash(key))  # type: ignore

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

    @instrument_class_function(name="merge", level=logging.DEBUG)
    def merge(self, other: DataCenter) -> None:
        """
        Merge two data centers together
        :param other: data center to merge with
        :return: None
        """
        for number, row in other.items():
            if number in self.keys():
                for cabinet in row:
                    if cabinet not in self[number]:
                        self[number].append(cabinet)
                    else:
                        self[number][self[number].index(cabinet)].merge(cabinet)
            else:
                self[number] = row
        self.clear_changes()

    def __eq__(self, other) -> bool:
        if not isinstance(other, DataCenter):
            return False
        return self.name == other.name

    def __setitem__(self, key: int, item: List[Cabinet]) -> None:
        # glue all handlers to event invocation
        for cabinet in item:
            for server in cabinet.servers:
                server.disks.add_listeners(self.invoke_listeners)
            cabinet.servers.add_listeners(self.invoke_listeners)
            for chassis in cabinet.chassis:
                for blade in chassis.blades:
                    for node in blade.nodes:
                        for module in node.modules:
                            module.disks.add_listeners(self.invoke_listeners)
                        node.modules.add_listeners(self.invoke_listeners)
                    blade.nodes.add_listeners(self.invoke_listeners)
                chassis.blades.add_listeners(self.invoke_listeners)
            cabinet.chassis.add_listeners(self.invoke_listeners)
            cabinet.switches.add_listeners(self.invoke_listeners)
        # insert the row
        self.rows.set(key, item, hash(key))  # type: ignore

    @instrument_class_function(name="getitem", level=logging.DEBUG)
    def __getitem__(self, key) -> List[Cabinet]:
        for k, v in self.rows.read().items():
            if k == key:
                return v
        raise KeyError(f"Key {key} not found")

    @instrument_class_function(name="delitem", level=logging.DEBUG)
    def __delitem__(self, key) -> None:
        for k, v in self.rows.read().items():
            if k == key:
                # remove all listeners
                for cabinet in v:
                    for server in cabinet.servers:
                        server.disks.remove_listeners(self.invoke_listeners)
                    cabinet.servers.remove_listeners(self.invoke_listeners)
                    for chassis in cabinet.chassis:
                        for blade in chassis.blades:
                            for node in blade.nodes:
                                for module in node.modules:
                                    module.disks.remove_listeners(self.invoke_listeners)
                                node.modules.remove_listeners(self.invoke_listeners)
                            blade.nodes.remove_listeners(self.invoke_listeners)
                        chassis.blades.remove_listeners(self.invoke_listeners)
                    cabinet.chassis.remove_listeners(self.invoke_listeners)
                    cabinet.switches.remove_listeners(self.invoke_listeners)
                # remove the row
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

    def __eq__(self, other) -> bool:
        if not isinstance(other, DataCenterNetwork):
            return False
        return self.name == other.name and self.network_type == other.network_type

    def __hash__(self):
        return hash((self.name, self.network_type))

    @instrument_class_function(name="merge", level=logging.DEBUG)
    def merge(self, other: DataCenterNetwork) -> None:
        """
        Merge two networks together
        :param other: network to merge with
        :return: None
        """
        for node in other.graph.nodes:
            if node not in self.graph.nodes:
                self.graph.add_node(node)
        for edge in other.graph.edges:
            if edge not in self.graph.edges:
                self.graph.add_edge(edge[0], edge[1])

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
                f"No free ports available on {left} ({left.number}:{left.serial_number})"
            )
        if isinstance(right, NetworkDevice):
            right_port = next(iter([r for r in right.ports if not r.connected]), None)
        else:
            # we assume that if it isn't a network device, it is a computer
            right_port = next(
                iter([r for n in right.nics for r in n.ports if not r.connected]), None  # type: ignore
            )
        if not right_port:
            raise ValueError(
                f"No free ports available on {right} ({right.number}:{right.serial_number})"
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
                iter([r for n in right.nics for r in n.ports if r.connected]), None  # type: ignore
            )
        if not left_port or not right_port:
            raise ValueError(
                f"could not determine connected ports for {left} and {right}"
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
                    iter([l for ni in n.nics for l in ni if l.connected]), None  # type: ignore
                )
            else:
                left_port = next(iter([l for l in n.ports if l.connected]), None)
            if left_port:
                left_port.status = DeviceStatus.Down
        if isinstance(device, NetworkDevice):
            for port in device.ports:
                port.status = (
                    DeviceStatus.Down
                    if port.status == DeviceStatus.Up
                    else DeviceStatus.Up
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
            for nic in device.nics:  # type: ignore
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
