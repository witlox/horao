# -*- coding: utf-8 -*-#
"""Various types of computers and their properties"""
from __future__ import annotations

from abc import ABC
from typing import List, Optional, TypeVar

from horao.conceptual.crdt import CRDTList, LastWriterWinsMap
from horao.logical.resource import Compute
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.hardware import Hardware, HardwareList
from horao.physical.network import NIC
from horao.physical.status import DeviceStatus


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

    def __eq__(self, other) -> bool:
        """
        Compare two computers, note that names are assumed to be unique
        :param other: instance of Computer
        :return: bool
        """
        if not isinstance(other, Computer):
            return False
        if self.serial_number != other.serial_number:
            return False
        if not self.name == other.name:
            return False
        return True

    def __gt__(self, other) -> bool:
        return self.number > other.number

    def __lt__(self, other) -> bool:
        return self.number < other.number

    def __hash__(self) -> int:
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


T = TypeVar("T", bound=Computer)


class ComputerList(CRDTList[T]):
    def __init__(
        self,
        computers: Optional[List[T]] = None,
        items: Optional[LastWriterWinsMap] = None,
    ):
        super().__init__(computers, items)
