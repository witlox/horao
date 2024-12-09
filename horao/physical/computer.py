# -*- coding: utf-8 -*-#
"""Various types of computers and their properties"""
from __future__ import annotations

from abc import ABC
from typing import List, Optional, TypeVar

from horao.conceptual.crdt import CRDTList, LastWriterWinsMap
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.hardware import HardwareList
from horao.physical.network import NIC
from horao.physical.status import DeviceStatus


class Computer(ABC):
    def __init__(
        self,
        serial_number: str,
        name: str,
        model: str,
        number: int,
        cpus: List[CPU] | HardwareList[CPU],
        rams: List[RAM] | HardwareList[RAM],
        nics: List[NIC] | HardwareList[NIC],
        disks: Optional[List[Disk]] | Optional[HardwareList[Disk]],
        accelerators: Optional[List[Accelerator]] | Optional[HardwareList[Accelerator]],
    ):
        self.serial_number = serial_number
        self.name = name
        self.model = model
        self.number = number
        self._cpus = HardwareList[CPU](
            hardware=cpus if isinstance(cpus, list) else None,
            items=cpus if isinstance(cpus, HardwareList) else None,  # type: ignore
        )
        self._rams = HardwareList[RAM](
            hardware=rams if isinstance(rams, list) else None,
            items=rams if isinstance(rams, HardwareList) else None,  # type: ignore
        )
        self._nics = HardwareList[NIC](
            hardware=nics if isinstance(nics, list) else None,
            items=nics if isinstance(nics, HardwareList) else None,  # type: ignore
        )
        self._disks = HardwareList[Disk](
            hardware=disks if isinstance(disks, list) else None,
            items=disks if isinstance(disks, HardwareList) else None,  # type: ignore
        )
        self._accelerators = HardwareList[Accelerator](
            hardware=accelerators if isinstance(accelerators, list) else None,
            items=accelerators if isinstance(accelerators, HardwareList) else None,  # type: ignore
        )

    def add_listener(self, listener):
        if listener not in self._disks.listeners:
            self._disks.add_listeners(listener)

    def remove_listener(self, listener):
        if listener in self._disks.listeners:
            self._disks.remove_listeners(listener)

    @property
    def cpus(self) -> List[CPU]:
        return list(iter(self._cpus))

    @property
    def rams(self) -> List[RAM]:
        return list(iter(self._rams))

    @property
    def nics(self) -> List[NIC]:
        return list(iter(self._nics))

    @property
    def disks(self) -> List[Disk]:
        return list(iter(self._disks))

    @property
    def accelerators(self) -> List[Accelerator]:
        return list(iter(self._accelerators))

    def change_count(self) -> int:
        """
        Return the number of changes in the stack
        :return: int
        """
        return (
            self._cpus.change_count()
            + self._rams.change_count()
            + self._nics.change_count()
            + self._disks.change_count()
            + self._accelerators.change_count()
        )

    def __copy__(self):
        return Computer(
            self.serial_number,
            self.name,
            self.model,
            self.number,
            self.cpus,
            self.rams,
            self.nics,
            self.disks,
            self.accelerators,
        )

    def __eq__(self, other) -> bool:
        """
        Compare two computers, note that names are assumed to be unique
        :param other: instance of Computer
        :return: bool
        """
        if not isinstance(other, Computer):
            return False
        return (
            self.serial_number == other.serial_number
            and self.name == other.name
            and self.model == other.model
            and self.cpus == other.cpus
            and self.rams == other.rams
            and self.nics == other.nics
            and self.disks == other.disks
            and self.accelerators == other.accelerators
        )

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
        cpus: List[CPU] | HardwareList[CPU],
        rams: List[RAM] | HardwareList[RAM],
        nics: List[NIC] | HardwareList[NIC],
        disks: Optional[List[Disk]] | Optional[HardwareList[Disk]],
        accelerators: Optional[List[Accelerator]] | Optional[HardwareList[Accelerator]],
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
            self.cpus,
            self.rams,
            self.nics,
            self.disks,
            self.accelerators,
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
        cpus: List[CPU] | HardwareList[CPU],
        rams: List[RAM] | HardwareList[RAM],
        nics: List[NIC] | HardwareList[NIC],
        disks: Optional[List[Disk]] | Optional[HardwareList[Disk]],
        accelerators: Optional[List[Accelerator]] | Optional[HardwareList[Accelerator]],
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
