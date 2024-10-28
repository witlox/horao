# -*- coding: utf-8 -*-#
"""Composite hardware models, e.g. servers, blades, nodes, etc."""
from __future__ import annotations

from abc import ABC
from typing import List, Optional, TypeVar

from horao.models.components import CPU, RAM, Accelerator, Disk, Hardware, HardwareList
from horao.models.crdt import CRDTList, LastWriterWinsMap
from horao.models.network import NIC, DeviceStatus


class Computer(ABC):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self.cpus = HardwareList[CPU](cpus)
        self.rams = HardwareList[RAM](rams)
        self.nics = HardwareList[NIC](nics)
        self.disks = HardwareList[Disk](disks)
        self.accelerators = HardwareList[Accelerator](accelerators)

    def __copy__(self):
        return Computer(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.cpus)),
            list(iter(self.rams)),
            list(iter(self.nics)),
            list(iter(self.disks)),
            list(iter(self.accelerators)),
        )

    def __eq__(self, other):
        """
        Compare two computers, note that names are assumed to be unique
        :param other: instance of Computer
        :return: bool
        """
        if not isinstance(other, Hardware):
            return False
        if self.serial_number != other.serial_number:
            return False
        if not self.name == other.name:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return self.number > other.number

    def __lt__(self, other):
        return self.number < other.number

    def __hash__(self):
        return hash(self.serial_number)


class Server(Computer):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
        status: DeviceStatus,
    ):
        super().__init__(
            serial_number, name, model, number, cpus, rams, nics, disks, accelerators
        )
        self.status = status

    def __copy__(self):
        return Server(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            list(iter(self.cpus)),
            list(iter(self.rams)),
            list(iter(self.nics)),
            list(iter(self.disks)),
            list(iter(self.accelerators)),
            self.status,
        )


class Module(Server):
    """A module is a compute component that can be added to a node"""

    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU],
        rams: List[RAM],
        nics: List[NIC],
        disks: Optional[List[Disk]],
        accelerators: Optional[List[Accelerator]],
        status: DeviceStatus,
    ):
        super().__init__(
            serial_number,
            name,
            model,
            number,
            cpus,
            rams,
            nics,
            disks,
            accelerators,
            status,
        )


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


T = TypeVar("T", bound=Computer)


class ComputerList(CRDTList[T]):
    def __init__(self, computers: List[T] = None, items: LastWriterWinsMap = None):
        super().__init__(computers, items)
