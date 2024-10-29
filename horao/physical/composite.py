# -*- coding: utf-8 -*-#
"""Composite hardware models that do not consist of 'compute', 'storage' or 'network'."""
from __future__ import annotations

from typing import List, Optional

from horao.physical.computer import Server, Module, ComputerList
from horao.physical.hardware import Hardware, HardwareList
from horao.physical.network import DeviceStatus, Switch, NetworkList


class Node(Hardware):
    """A node is a physical container that can host multiple modules"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        modules: Optional[List[Module]],
        status: DeviceStatus,
    ):
        super().__init__(serial_number, name, model, number)
        self.modules = ComputerList[Module](modules)
        self.status = status

    def __copy__(self):
        return Node(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.modules)),
            self.status,
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
        status: DeviceStatus,
    ):
        super().__init__(serial_number, name, model, number)
        self.nodes = HardwareList[Node](nodes)
        self.status = status

    def __copy__(self):
        return Blade(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.nodes)),
            self.status,
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
        super().__init__(serial_number, name, model, number)
        self.servers = ComputerList[Server](servers)
        self.blades = HardwareList[Blade](blades)

    def __copy__(self):
        return Chassis(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.servers)),
            list(iter(self.blades)),
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
        super().__init__(serial_number, name, model, number)
        self.servers = ComputerList[Server](servers)
        self.chassis = HardwareList[Chassis](chassis)
        self.switches = NetworkList[Switch](switches)

    def __copy__(self):
        return Cabinet(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.servers)),
            list(iter(self.chassis)),
            list(iter(self.switches)),
        )
