# -*- coding: utf-8 -*-#
"""Composite hardware models that do not consist of 'compute', 'storage' or 'network'."""
from __future__ import annotations

from typing import List, Optional

from horao.physical.computer import ComputerList, Module, Server
from horao.physical.hardware import Hardware, HardwareList
from horao.physical.network import NetworkList, Switch


class Node(Hardware):
    """A node is a physical container that can host multiple modules"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        modules: Optional[List[Module]],
    ):
        super().__init__(serial_number, model, number)
        self.name = name
        self._modules = ComputerList[Module](modules)

    @property
    def modules(self):
        return list(iter(self._modules))

    def __copy__(self):
        return Node(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.modules,
        )


class Blade(Hardware):
    """A blade is a physical container that can host one or multiple nodes"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        nodes: Optional[List[Node]],
    ):
        super().__init__(serial_number, model, number)
        self.name = name
        self._nodes = HardwareList[Node](nodes)

    def add_listener(self, listener):
        if listener not in self._nodes.listeners:
            self._nodes.add_listeners(listener)

    def remove_listener(self, listener):
        if listener in self._nodes.listeners:
            self._nodes.remove_listeners(listener)

    @property
    def nodes(self):
        return list(iter(self._nodes))

    def change_count(self) -> int:
        return self._nodes.change_count()

    def __copy__(self):
        return Blade(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.nodes,
        )


class Chassis(Hardware):
    """A chassis hosts servers and/or blades"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: Optional[List[Server]],
        blades: Optional[List[Blade]],
    ):
        super().__init__(serial_number, model, number)
        self.name = name
        self._servers = ComputerList[Server](servers)
        self._blades = HardwareList[Blade](blades)

    def add_listener(self, listener):
        if listener not in self._servers.listeners:
            self._servers.add_listeners(listener)
        if listener not in self._blades.listeners:
            self._blades.add_listeners(listener)

    def remove_listener(self, listener):
        if listener in self._servers.listeners:
            self._servers.remove_listeners(listener)
        if listener in self._blades.listeners:
            self._blades.remove_listeners(listener)

    @property
    def servers(self):
        return list(iter(self._servers))

    @property
    def blades(self):
        return list(iter(self._blades))

    def change_count(self) -> int:
        return self._servers.change_count() + self._blades.change_count()

    def __copy__(self):
        return Chassis(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.servers,
            self.blades,
        )


class Cabinet(Hardware):
    """A cabinet is a physical rack that hosts servers, chassis, and switches"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        servers: Optional[List[Server]],
        chassis: Optional[List[Chassis]],
        switches: Optional[List[Switch]],
    ):
        super().__init__(serial_number, model, number)
        self.name = name
        self._servers = ComputerList[Server](servers)
        self._chassis = HardwareList[Chassis](chassis)
        self._switches = NetworkList[Switch](switches)

    def add_listener(self, listener):
        if listener not in self._servers.listeners:
            self._servers.add_listeners(listener)
        if listener not in self._chassis.listeners:
            self._chassis.add_listeners(listener)
        if listener not in self._switches.listeners:
            self._switches.add_listeners(listener)

    def remove_listener(self, listener):
        if listener in self._servers.listeners:
            self._servers.remove_listeners(listener)
        if listener in self._chassis.listeners:
            self._chassis.remove_listeners(listener)
        if listener in self._switches.listeners:
            self._switches.remove_listeners(listener)

    @property
    def servers(self):
        return list(iter(self._servers))

    @property
    def chassis(self):
        return list(iter(self._chassis))

    @property
    def switches(self):
        return list(iter(self._switches))

    def change_count(self) -> int:
        return (
            self._servers.change_count()
            + self._chassis.change_count()
            + self._switches.change_count()
        )

    def merge(self, other: Cabinet, reset_counters: bool = False) -> None:
        self.servers.extend(iter(other.servers))
        self.chassis.extend(iter(other.chassis))
        self.switches.extend(iter(other.switches))
        if reset_counters:
            self._servers.reset_change_count()
            self._chassis.reset_change_count()
            self._switches.reset_change_count()

    def __copy__(self):
        return Cabinet(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.servers,
            self.chassis,
            self.switches,
        )
