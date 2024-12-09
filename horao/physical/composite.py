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
        self.modules = ComputerList[Module](modules)

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
        self.nodes = HardwareList[Node](nodes)

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
        self.servers = ComputerList[Server](servers)
        self.blades = HardwareList[Blade](blades)

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
        self.servers = ComputerList[Server](servers)
        self.chassis = HardwareList[Chassis](chassis)
        self.switches = NetworkList[Switch](switches)

    def merge(self, other: Cabinet, clear_history: bool = True) -> None:
        """
        Merge the cabinet with another cabinet
        :param other: cabinet to merge with
        :param clear_history: clear change history
        :return: None
        """
        self.servers.extend(iter(other.servers))
        self.chassis.extend(iter(other.chassis))
        self.switches.extend(iter(other.switches))
        if clear_history:
            self.servers.clear_history()
            self.chassis.clear_history()
            self.switches.clear_history()

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
